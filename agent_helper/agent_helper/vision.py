"""پیوست تصویر در چت: ذخیره‌ی امن و استخراج اطلاعات (مثلاً فاکتور) با مدل بینایی.

استخراج یک مرحله‌ی جدا و مستقل از حلقه‌ی ابزار است؛ نتیجه (متن) به پیام کاربر اضافه می‌شود تا در نوبت‌های بعدی
هم در تاریخچه بماند و مدل اصلی بدون نیاز به بینایی ادامه دهد. مدل بینایی با ASSISTANT_VISION_* جدا قابل تنظیم است
و پیش‌فرضش همان تنظیمات ASSISTANT_LLM_* است.
"""
import base64
import binascii
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, Optional

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from agent_helper import conf
from agent_helper.fa import to_ascii_digits as normalize_digits

logger = logging.getLogger(__name__)

ALLOWED = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}
DATA_URL_RE = re.compile(r'^data:(image/[a-z]+);base64,(.+)$', re.S)

EXTRACT_PROMPT = (
    'این تصویر یک سند (معمولاً فاکتور) فارسی است. همه‌ی اطلاعات خوانا را دقیق استخراج کن و فقط یک JSON معتبر برگردان، بدون توضیح. '
    'کلیدها: seller (نام فروشنده)، buyer (نام خریدار)، invoice_number، date (همان‌طور که در تصویر نوشته شده)، '
    'items (آرایه‌ای از {name, quantity, unit, unit_price, amount})، subtotal (جمع اقلام)، discount، tax، total (مبلغ نهایی)، '
    'currency (ریال یا تومان، همان‌طور که در تصویر آمده)، notes. '
    'همه‌ی ارقام را انگلیسی و بدون جداکننده بنویس. چیزی را که در تصویر نیست یا واضح نخواندی null بگذار؛ هرگز حدس نزن.'
)


def _cfg():
    base = (conf.get('VISION_BASE_URL') or conf.get('LLM_BASE_URL') or '').rstrip('/')
    return {
        'url': base + '/chat/completions' if base else '',
        'key': conf.get('VISION_API_KEY') or conf.get('LLM_API_KEY'),
        'model': conf.get('VISION_MODEL') or conf.get('LLM_MODEL'),
        'timeout': int(conf.get('VISION_TIMEOUT')),
    }


def save_upload(user, data_url: str) -> str:
    """تصویر base64 را اعتبارسنجی و ذخیره می‌کند؛ مسیر نسبی در storage را برمی‌گرداند. ValueError با پیام فارسی"""
    m = DATA_URL_RE.match((data_url or '').strip())
    if not m or m.group(1) not in ALLOWED:
        raise ValueError('فقط تصویر png، jpg یا webp پذیرفته می‌شود.')
    try:
        raw = base64.b64decode(m.group(2), validate=False)
    except (binascii.Error, ValueError):
        raise ValueError('فایل تصویر معتبر نیست.')
    max_bytes = int(conf.get('MAX_UPLOAD_BYTES'))
    if not raw or len(raw) > max_bytes:
        raise ValueError(f'حجم تصویر باید کمتر از {max_bytes // (1024 * 1024)} مگابایت باشد.'.translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')))
    name = f'{conf.get("UPLOAD_DIR")}/{user.id}/{uuid.uuid4().hex}.{ALLOWED[m.group(1)]}'
    return default_storage.save(name, ContentFile(raw))


def _data_url(path: str) -> str:
    ext = path.rsplit('.', 1)[-1].lower()
    mime = next(k for k, v in ALLOWED.items() if v == ext)
    with default_storage.open(path, 'rb') as fh:
        return f'data:{mime};base64,' + base64.b64encode(fh.read()).decode()


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or '').strip()
    text = re.sub(r'^```(?:json)?|```$', '', text, flags=re.M).strip()
    try:
        data = json.loads(text)
    except ValueError:
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None
    return data if isinstance(data, dict) else None


def _num(v) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = normalize_digits(str(v)).replace(',', '').replace('٬', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def check_totals(data: Dict[str, Any]) -> str:
    """کنترل حسابی روی داده‌ی استخراج‌شده؛ در صورت مغایرت، پیام هشدار (فارسی) برمی‌گرداند"""
    items = data.get('items') if isinstance(data.get('items'), list) else []
    amounts = [_num(i.get('amount')) for i in items if isinstance(i, dict)]
    warnings = []
    if items and all(a is not None for a in amounts):
        total_items = sum(amounts)
        subtotal = _num(data.get('subtotal'))
        if subtotal is not None and abs(total_items - subtotal) > 1:
            warnings.append('جمع مبلغ اقلام با «جمع اقلام» نمی‌خواند')
        subtotal = subtotal if subtotal is not None else total_items
        total = _num(data.get('total'))
        if total is not None:
            expected = subtotal - (_num(data.get('discount')) or 0) + (_num(data.get('tax')) or 0)
            if abs(expected - total) > 1:
                warnings.append('جمع اقلام منهای تخفیف به‌علاوه‌ی مالیات با مبلغ نهایی نمی‌خواند')
    for item in items:
        if not isinstance(item, dict):
            continue
        q, u, a = _num(item.get('quantity')), _num(item.get('unit_price')), _num(item.get('amount'))
        if None not in (q, u, a) and abs(q * u - a) > 1:
            warnings.append(f'در قلم «{item.get("name")}» تعداد × قیمت واحد با مبلغ نمی‌خواند')
    return '؛ '.join(warnings)


def extract_document(path: str, trace=None) -> Dict[str, Any]:
    """اطلاعات تصویر را استخراج می‌کند. نتیجه: {'text': متن آماده‌ی افزودن به پیام, 'data': dict یا None, 'warning': str}"""
    cfg = _cfg()
    body = {'model': cfg['model'], 'stream': False, 'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': EXTRACT_PROMPT},
        {'type': 'image_url', 'image_url': {'url': _data_url(path)}}]}]}
    started = time.time()
    content, usage, error = '', {}, ''
    for attempt in range(3):  # دروازه گاهی پاسخ خالی (in_progress) می‌دهد
        try:
            resp = requests.post(cfg['url'], json=body, headers={'Authorization': 'Bearer ' + cfg['key']}, timeout=cfg['timeout'])
            resp.raise_for_status()
            payload = resp.json()
            content = (payload['choices'][0]['message'].get('content') or '').strip()
            usage = payload.get('usage') or {}
            if content:
                break
            error = 'پاسخ خالی'
        except (requests.RequestException, KeyError, ValueError) as e:
            error = f'{type(e).__name__}: {e}'
            logger.warning('Vision extract attempt %s failed: %s', attempt + 1, error)
    ok = bool(content)
    if trace is not None:
        trace.model_call('vision', 'openai', cfg['model'], ok=ok, ms=int((time.time() - started) * 1000),
                         input_tokens=usage.get('prompt_tokens', 0), output_tokens=usage.get('completion_tokens', 0),
                         error='' if ok else error, attempts=attempt + 1)
    if not ok:
        return {'text': '', 'data': None, 'warning': '', 'error': 'خواندن تصویر انجام نشد.'}
    data = _parse_json(content)
    warning = check_totals(data) if data else ''
    shown = json.dumps(data, ensure_ascii=False) if data else content
    text = ('\n\n[تصویر پیوست شد. اطلاعات استخراج‌شده‌ی ماشینی از آن (ممکن است خطا داشته باشد؛ مقدارهای مبهم را از کاربر تأیید بگیر): '
            + shown + ']')
    if warning:
        text += f'\n[هشدار کنترل حسابی: {warning}. قبل از ثبت، مبلغ‌ها را حتماً با کاربر مرور کن.]'
    return {'text': text, 'data': data, 'warning': warning}

"""Persian text helpers: digits, normalization, amounts written with digits or words.

Amounts are always extracted by code (a classifier is not a calculator).
"""
import re

_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬،', '01234567890123456789.,,')
_ASCII_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')

UNITS = {'صفر': 0, 'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5, 'شش': 6, 'شیش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9,
         'ده': 10, 'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14, 'پانزده': 15, 'شانزده': 16, 'هفده': 17,
         'هجده': 18, 'نوزده': 19, 'بیست': 20, 'سی': 30, 'چهل': 40, 'پنجاه': 50, 'شصت': 60, 'هفتاد': 70, 'هشتاد': 80,
         'نود': 90, 'صد': 100, 'یکصد': 100, 'دویست': 200, 'سیصد': 300, 'چهارصد': 400, 'پانصد': 500, 'ششصد': 600,
         'هفتصد': 700, 'هشتصد': 800, 'نهصد': 900}
MULTIPLIERS = {'هزار': 10 ** 3, 'میلیون': 10 ** 6, 'ملیون': 10 ** 6, 'میلیارد': 10 ** 9, 'بیلیون': 10 ** 9}


def to_ascii_digits(value):
    """Persian/Arabic digits to ASCII (falsy values are returned unchanged)"""
    if not value:
        return value
    return value.translate(_ASCII_DIGITS)


def fa_number(n) -> str:
    """1234 -> '۱,۲۳۴'"""
    return f'{int(n):,}'.translate(_FA_DIGITS)


def normalize(text: str) -> str:
    text = (text or '').translate(_DIGITS).replace('‌', ' ').replace('ي', 'ی').replace('ك', 'ک')
    return re.sub(r'\s+', ' ', text).strip()


def normalize_digits_text(text: str) -> str:
    return text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')).replace('ي', 'ی').replace('ك', 'ک')


def extract_currency(text: str) -> str | None:
    t = normalize(text)
    if re.search(r'ریال|rial', t):
        return 'rial'
    if re.search(r'تومان|تومن|toman', t):
        return 'toman'
    return None


def extract_amount(text: str) -> int | None:
    """اولین مبلغ متن را برمی‌گرداند (در همان واحدی که کاربر گفته؛ مثلاً «بیست میلیون» ⇒ 20000000)"""
    tokens = re.findall(r'\d+(?:[.,]\d+)*|[^\s\d.,،؛؟?!:()«»"\']+', normalize(text))
    # «۵۵ میلیونی»، «۲ میلیاردی» ⇒ ضریب بدون «ی»
    tokens = [t[:-1] if t.endswith('ی') and t[:-1] in MULTIPLIERS else t for t in tokens]
    span, i = [], 0
    while i < len(tokens):
        tk = tokens[i]
        is_num = re.fullmatch(r'\d+(?:[.,]\d+)*', tk) or tk in UNITS or tk in MULTIPLIERS
        if is_num:
            span.append(tk)
        elif tk == 'و' and span and i + 1 < len(tokens) and (tokens[i + 1] in UNITS or tokens[i + 1] in MULTIPLIERS):
            span.append(tk)
        elif span:
            break
        i += 1
    if not span:
        return None
    # عدد حروفی خالی («یک»، «سه») اغلب حرف نکره/توصیفی است؛ مبلغ باید رقم یا ضریب (هزار/میلیون/...) داشته باشد
    if not any(re.fullmatch(r'\d+(?:[.,]\d+)*', tk) or tk in MULTIPLIERS for tk in span):
        return None
    total, current = 0, 0
    for tk in span:
        if tk == 'و':
            continue
        if re.fullmatch(r'\d+(?:[.,]\d+)*', tk):
            raw = tk.replace(',', '')
            current += float(raw) if '.' in raw else int(raw)
        elif tk in UNITS:
            current += UNITS[tk]
        else:
            current = (current or 1) * MULTIPLIERS[tk]
            total += current
            current = 0
    value = total + current
    return int(round(value)) if value else None

"""Light classifiers for the fast route: Jev (TypeSafe System One ``/v1/systemone``) or any OpenAI-compatible local
model that returns logprobs. Questions are collected from the registered plugins (FastRoutes and catalogs).

The classifier only takes qualitative decisions; amounts and ids are always parsed by code.
"""
import json
import math
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from agent_helper import conf
from agent_helper.plugins import CatalogEntry, CatalogProvider
from agent_helper.registry import registry


class JevError(Exception):
    pass


# ----------------------------------------------------------------------------- questions

def main_questions() -> Dict[str, dict]:
    """Choice questions of the main routes (asked by both backends), in route order"""
    out: Dict[str, dict] = {}
    for route in registry.routes():
        out.update(route.questions)
    return out


def gate_questions() -> Dict[str, dict]:
    """Yes/no questions of the gate routes: ``is_<route name>``"""
    return {r.gate_key: r.gate_question for r in registry.routes() if r.gate_question}


def catalog_question(provider: CatalogProvider) -> Optional[dict]:
    """«Which one?» choice question built from a catalog (keys = entry keys, plus 'none'); None if empty or failing"""
    try:
        entries = list(provider.entries())
    except Exception:  # noqa: BLE001 - a broken catalog must not break routing
        return None
    if not entries:
        return None
    criteria = {}
    for entry in entries:
        names = [entry.title] + [a for a in entry.aliases if a != entry.title]
        criteria[str(entry.key)] = ' / '.join(names) + (f' — {entry.description}' if entry.description else '')
    criteria['none'] = provider.none_label
    return {'type': 'choice', 'instructions': provider.instructions, 'criteria': criteria}


def jev_questions() -> Dict[str, dict]:
    questions = main_questions()
    questions.update(gate_questions())
    for provider in registry.catalogs():
        q = catalog_question(provider)
        if q:
            questions[provider.question_key] = q
    return questions


# ----------------------------------------------------------------------------- backends

def jev_classify(text: str, timeout: float = 4.0) -> dict:
    """یک درخواست Jev با چند سؤال موازی. برمی‌گرداند: {question: {'choice', 'confidence'}}؛
    سؤال‌های بله/خیر (is_*) علاوه بر آن کلید 'p' (احتمال «بله») دارند. usage/زمان در _usage/_ms"""
    api_key = conf.get('JEV_API_KEY')
    if not api_key:
        raise JevError('TYPESAFE_API_KEY تنظیم نشده')
    base = (conf.get('JEV_BASE_URL') or '').rstrip('/')
    if not base:
        raise JevError('TYPESAFE_BASE_URL تنظیم نشده')
    body = {'state': text, 'model': conf.get('JEV_MODEL'), 'questions': jev_questions()}
    req = urllib.request.Request(base + '/v1/systemone', data=json.dumps(body).encode(), headers={
        'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    started = time.time()
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        raise JevError(f'HTTP {e.code}')
    except Exception as e:
        raise JevError(f'{type(e).__name__}: {e}')
    out = {}
    for k, v in data['answers'].items():
        if 'noul' in v:
            p = v['noul']
            out[k] = {'choice': 'yes' if p >= 0.5 else 'no', 'confidence': max(p, 1 - p), 'p': p}
        else:
            out[k] = {'choice': v['choice'], 'confidence': v['confidence']}
    out['_usage'] = data.get('usage', {})
    out['_ms'] = int((time.time() - started) * 1000)
    return out


def llm_classify(text: str, timeout: float = 10.0) -> dict:
    """تشخیص نیت با هر مدل لوکال/متن‌باز که API سازگار با OpenAI و logprobs بدهد (vLLM، llama.cpp، ollama).

    هر سؤال یک انتخاب تک‌حرفی است و confidence از احتمال توکن اول می‌آید (نرمال‌شده روی گزینه‌های معتبر).
    فقط سؤال‌های اصلی مسیرها پرسیده می‌شوند (نه سؤال‌های بله/خیر و کاتالوگ).
    تنظیم: INTENT_BASE_URL / _API_KEY / _MODEL (پیش‌فرض: همان LLM_*).
    """
    base = (conf.get('INTENT_BASE_URL') or conf.get('LLM_BASE_URL') or '').rstrip('/')
    key = conf.get('INTENT_API_KEY') or conf.get('LLM_API_KEY')
    model = conf.get('INTENT_MODEL') or conf.get('LLM_MODEL')
    if not base or not model:
        raise JevError('ASSISTANT_INTENT_BASE_URL/MODEL تنظیم نشده')
    questions = main_questions()
    if not questions:
        raise JevError('هیچ سؤالی برای تشخیص نیت ثبت نشده')
    letters = 'ABCDEFGH'
    started = time.time()

    def ask(item):
        name, q = item
        keys = list(q['criteria'])
        options = '\n'.join(f'{letters[i]}) {desc}' for i, desc in enumerate(q['criteria'].values()))
        body = {
            'model': model, 'temperature': 0, 'max_tokens': 3, 'logprobs': True, 'top_logprobs': 10,
            'messages': [
                {'role': 'system', 'content': 'You are a strict classifier. Reply with only the letter of the best option.'},
                {'role': 'user', 'content': f'{q["instructions"]}\n\nText: "{text}"\n\nOptions:\n{options}\n\nAnswer with a single letter.'},
            ],
        }
        req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(), headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        except Exception as e:
            raise JevError(f'{type(e).__name__}: {e}')
        try:
            top = data['choices'][0]['logprobs']['content'][0]['top_logprobs']
        except (KeyError, IndexError, TypeError):
            raise JevError('مدل logprobs برنمی‌گرداند')
        probs = {}
        for t in top:
            letter = t['token'].strip().upper()[:1]
            if letter in letters[:len(keys)]:
                probs[letter] = probs.get(letter, 0) + math.exp(t['logprob'])
        total = sum(probs.values())
        if not total:
            raise JevError('پاسخ مدل گزینه‌ی معتبر نبود')
        best = max(probs, key=probs.get)
        return name, {'choice': keys[letters.index(best)], 'confidence': probs[best] / total}

    with ThreadPoolExecutor(max_workers=len(questions)) as pool:
        out = dict(pool.map(ask, questions.items()))
    out['_usage'] = {}
    out['_ms'] = int((time.time() - started) * 1000)
    return out


def backend_name() -> str:
    return str(conf.get('INTENT_BACKEND') or 'jev').strip().lower()


def model_name() -> str:
    return (conf.get('INTENT_MODEL') or '') if backend_name() == 'llm' else conf.get('JEV_MODEL')


def classify(text: str) -> dict:
    """backend تشخیص نیت بر اساس INTENT_BACKEND: jev (پیش‌فرض) یا llm"""
    return llm_classify(text) if backend_name() == 'llm' else jev_classify(text, timeout=float(conf.get('INTENT_TIMEOUT')))


# ----------------------------------------------------------------------------- catalog matching

CATALOG_CONFIDENCE = 0.8


def match_catalog(provider: CatalogProvider, text: str, stopwords=()) -> Optional[CatalogEntry]:
    """Entry whose title or alias contains a word of the text (also without the last one or two letters, for
    Persian suffixes: «سفارشم» → سفارش); only if exactly one entry has the most matching words"""
    entries = list(provider.entries())
    found = {}
    for tok in re.split(r'[\s،؟?!.:؛]+', text):
        tok = tok.replace('‌', '')
        if tok in stopwords or len(tok) < 3:
            continue
        for cand in {tok, tok[:-1], tok[:-2]}:
            if len(cand) < 3 or cand in stopwords:
                continue
            for entry in entries:
                if any(cand in (n or '').replace('‌', '') for n in (entry.title,) + tuple(entry.aliases)):
                    found[entry.key] = found.get(entry.key, 0) + 1
    if not found:
        return None
    best = max(found.values())
    top = [key for key, n in found.items() if n == best]
    return next(e for e in entries if e.key == top[0]) if len(top) == 1 else None


def resolve_catalog(provider: CatalogProvider, cls: Optional[dict], text: str, stopwords=()) -> Optional[CatalogEntry]:
    """The classifier's choice if confident, otherwise text matching"""
    answer = (cls or {}).get(provider.question_key)
    if answer and answer['choice'] != 'none' and answer['confidence'] >= CATALOG_CONFIDENCE:
        entry = next((e for e in provider.entries() if str(e.key) == str(answer['choice'])), None)
        if entry:
            return entry
    return match_catalog(provider, text, stopwords)

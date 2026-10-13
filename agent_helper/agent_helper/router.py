"""Fast route: decide with cheap regexes and one light-classifier call (Jev or a local model), then run plugin
routes that call tools directly, without the LLM.

Used only when USE_FAST_ROUTER is on and the signals are confident; otherwise ``None`` is returned and the
normal LLM loop runs (full fallback). Nothing is executed here: routes may only read or propose
(PendingAction); the user confirms with the button.

Order of decisions:
1. disabled / conversation in a dialog mode (e.g. filling a form) -> LLM
2. gate routes whose regex guard matches (registration order)
3. one classifier call (errors -> LLM)
4. gate routes whose yes/no question is confident; two or more confident gates -> LLM (ambiguous)
5. main routes with the classifier answers
"""
import logging

from agent_helper import conf, nlu
from agent_helper.plugins import Defer, RouteRequest

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return conf.flag('USE_FAST_ROUTER')


def _defer(trace, reason):
    """رفتن به مسیر LLM همراه با ثبت دلیل در لاگ"""
    if trace is not None:
        trace.fast_reason = reason
    return None


def _finish(result, trace, default_reason):
    if isinstance(result, Defer):
        return _defer(trace, result.reason)
    if result is None:
        return _defer(trace, default_reason)
    return result


def _run_gate(route, req, trace):
    if route.handler is None:
        return _defer(trace, f'{route.name}_request')
    if trace is not None:
        trace.intent = route.name
    return _finish(route.handler(req), trace, f'{route.name}_unanswered')


def try_fast_path(user, conversation, text: str, trace=None):
    """برمی‌گرداند {'text': ..., 'events': [...], 'path': 'fast'} یا None برای رفتن به مسیر LLM"""
    from agent_helper.registry import registry
    if not enabled():
        return _defer(trace, 'disabled')
    # گفتگوی چندمرحله‌ای (مثلاً ثبت درخواست): پاسخ‌های کوتاه کاربر به سؤال دستیار نباید به مسیر سریع بروند
    mode = getattr(conversation, 'mode', '')
    if mode:
        return _defer(trace, f'{mode}_dialog')
    threshold = float(conf.get('FAST_THRESHOLD'))
    routes = registry.routes()
    gates = [r for r in routes if r.is_gate]

    def request(cls=None, gate_p=None):
        return RouteRequest(user=user, conversation=conversation, text=text, cls=cls, threshold=threshold,
                            gate_p=gate_p or {}, trace=trace)

    for route in gates:
        if route.guard is not None and route.guard(text):
            return _run_gate(route, request(), trace)

    backend, model = nlu.backend_name(), nlu.model_name()
    try:
        cls = nlu.classify(text)
    except Exception as e:  # خطا/timeout مدل سبک نباید پاسخ را خراب کند
        logger.warning('fast router classify failed: %s', e)
        if trace is not None:
            trace.model_call('intent', backend, model or '', ok=False, error=f'{type(e).__name__}: {e}')
        return _defer(trace, 'classifier_error')
    if trace is not None:
        trace.classification = cls  # برای انتخاب ابزارها اگر پیام به LLM برود
        trace.model_call('intent', backend, model or '', ok=True, ms=cls.get('_ms'),
                         input_tokens=cls.get('_usage', {}).get('input_tokens', 0),
                         output_tokens=cls.get('_usage', {}).get('output_tokens', 0),
                         detail={k: [v['choice'], round(v['confidence'], 3)] for k, v in cls.items() if not k.startswith('_')})
        if 'intent' in cls:
            trace.intent = cls['intent']['choice']
            trace.intent_confidence = round(cls['intent']['confidence'], 3)

    # سؤال‌های بله/خیر مسیرهای دروازه (فقط backend جو؛ مدل لوکال این کلیدها را ندارد)
    gate_p = {r.name: cls.get(r.gate_key, {}).get('p', 0) for r in gates if r.gate_question}
    sure = [r for r in gates if r.gate_question and gate_p[r.name] >= threshold]
    if len(sure) > 1:
        return _defer(trace, '_or_'.join(r.name for r in sure) + '_ambiguous')
    if sure:
        route = sure[0]
        if route.handler is None:
            return _defer(trace, f'{route.name}_request')
        if route.gate_veto is None or not route.gate_veto(text):
            return _run_gate(route, request(cls, gate_p), trace)

    req = request(cls, gate_p)
    for route in routes:
        if route.is_gate or route.handler is None:
            continue
        result = route.handler(req)
        if result is not None:
            return _finish(result, trace, 'no_route')
    return _defer(trace, 'no_route')

"""ثبت لاگ عملکرد دستیار: هر پیام، هر فراخوانی مدل و هر فراخوانی ابزار.

ثبت لاگ هرگز نباید پاسخ دستیار را خراب کند؛ هر خطای ذخیره‌سازی فقط در logger گزارش می‌شود.
"""
import logging
import time

logger = logging.getLogger(__name__)
MAX_MESSAGE = 1000
MAX_SUMMARY = 300


def _safe(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - لاگ نباید جلوی کار اصلی را بگیرد
            logger.warning('assistant trace failed (%s): %s', fn.__name__, e)
    return wrapper


class RequestTrace:
    """یک ردیف AssistantRequestLog به‌ازای هر پیام کاربر + زیرمجموعه‌ی لاگ مدل‌ها و ابزارها"""

    def __init__(self, user, conversation, message):
        self.log = None
        self.started = time.time()
        self.path = 'llm'
        self.status = 'ok'
        self.error = ''
        self.fast_reason = ''
        self.intent = ''
        self.intent_confidence = None
        self.intent_calls = self.llm_calls = self.tool_calls = 0
        self.input_tokens = self.output_tokens = 0
        self._finished = False
        self.classification = None   # پاسخ‌های مدل سبک (اگر مسیر سریع اجرا شد)
        self.tool_selection = 'all'  # برچسب‌های ابزارهایی که به LLM داده شد
        self._create(user, conversation, message)

    @_safe
    def _create(self, user, conversation, message):
        from agent_helper.models import AssistantRequestLog
        self.log = AssistantRequestLog.objects.create(
            user=user, conversation=conversation, message=(message or '')[:MAX_MESSAGE])

    # --- مدل‌ها
    @_safe
    def model_call(self, kind, backend, model, ok=True, ms=None, input_tokens=0, output_tokens=0,
                   error='', attempts=1, detail=None):
        if kind == 'intent':
            self.intent_calls += 1
        else:
            self.llm_calls += 1
        self.input_tokens += input_tokens or 0
        self.output_tokens += output_tokens or 0
        if self.log is None:
            return
        from agent_helper.models import ModelCallLog
        ModelCallLog.objects.create(
            request=self.log, kind=kind, backend=backend[:30], model=(model or '')[:80], ok=ok, error=(error or '')[:2000],
            attempts=attempts, input_tokens=input_tokens or 0, output_tokens=output_tokens or 0, duration_ms=ms, detail=detail or {})

    # --- ابزارها
    def run_tool(self, name, arguments, func):
        """ابزار را اجرا و لاگ می‌کند؛ نتیجه‌ی ابزار را دست‌نخورده برمی‌گرداند"""
        t0 = time.time()
        result, crashed = None, None
        try:
            result = func()
        except Exception as e:
            crashed = e
        ms = int((time.time() - t0) * 1000)
        self._tool_log(name, arguments, result, crashed, ms)
        if crashed:
            raise crashed
        return result

    @_safe
    def _tool_log(self, name, arguments, result, crashed, ms):
        self.tool_calls += 1
        if self.log is None:
            return
        from agent_helper.models import ToolCallLog
        ok = crashed is None and not (isinstance(result, dict) and result.get('error'))
        if crashed:
            summary = f'EXC {type(crashed).__name__}: {crashed}'
        elif isinstance(result, dict):
            summary = result.get('error') or result.get('message') or ', '.join(f'{k}={v}' for k, v in result.items() if isinstance(v, (int, str)) and k != 'items')
        else:
            summary = str(result)
        ToolCallLog.objects.create(request=self.log, name=name[:60], arguments=_json_safe(arguments), ok=ok,
                                   result_summary=summary[:MAX_SUMMARY], duration_ms=ms)

    # --- پایان
    def set_error(self, message):
        self.status = 'error'
        self.error = (message or '')[:2000]

    @_safe
    def finish(self):
        if self._finished:
            return
        self._finished = True
        if self.log is None:
            return
        log = self.log
        log.path = 'error' if self.status == 'error' and self.path != 'fast' else self.path
        log.status = self.status
        log.error = self.error
        log.fast_reason = self.fast_reason[:60]
        log.intent = self.intent[:20]
        log.intent_confidence = self.intent_confidence
        log.intent_calls, log.llm_calls, log.tool_calls = self.intent_calls, self.llm_calls, self.tool_calls
        log.input_tokens, log.output_tokens = self.input_tokens, self.output_tokens
        log.duration_ms = int((time.time() - self.started) * 1000)
        log.save()


def _json_safe(value):
    import json
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return {'repr': str(value)[:300]}

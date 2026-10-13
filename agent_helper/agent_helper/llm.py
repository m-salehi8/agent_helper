import json
import time
import logging
import requests
from django.conf import settings
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator
from dataclasses import dataclass, field

from agent_helper import conf
from agent_helper import tools as agent_tools
from agent_helper.actions import pending_event
from agent_helper.models import AssistantConversation, AssistantMessage

logger = logging.getLogger(__name__)

# سقف تکرار حلقه agent (پیش‌فرض؛ قابل تنظیم با AGENT_HELPER['MAX_AGENT_ITERATIONS'])
MAX_AGENT_ITERATIONS = 6


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


def _require_url(base_url: str):
    """No built-in public endpoint: the LLM server must be configured (offline deployments)"""
    if not base_url:
        raise requests.ConnectionError('ASSISTANT_LLM_BASE_URL (AGENT_HELPER LLM_BASE_URL) تنظیم نشده')


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        pass


class AnthropicProvider(LLMProvider):
    """پیاده‌سازی ارتباط با Anthropic Messages API با ابزارها"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30
    ):
        self.api_key = api_key or conf.get('LLM_API_KEY')
        self.model = model or conf.get('LLM_MODEL') or 'claude-3-5-sonnet-20241022'
        self.base_url = (base_url or conf.get('LLM_BASE_URL') or '').rstrip('/')
        self.timeout = int(conf.get('LLM_TIMEOUT') or timeout)

    def complete(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        _require_url(self.base_url)
        url = f"{self.base_url}/v1/messages"
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }

        payload: Dict[str, Any] = {
            'model': self.model,
            'max_tokens': 2048,
            'messages': messages,
        }
        if system:
            payload['system'] = system
        if tools:
            payload['tools'] = tools

        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)

        if resp.status_code == 429:
            raise requests.HTTPError('محدودیت نرخ درخواست (Rate Limit)', response=resp)
        resp.raise_for_status()

        data = resp.json()
        response_text = ""
        tool_calls = []

        for content_block in data.get('content', []):
            if content_block.get('type') == 'text':
                response_text += content_block.get('text', '')
            elif content_block.get('type') == 'tool_use':
                tool_calls.append(
                    ToolCall(
                        id=content_block.get('id', ''),
                        name=content_block.get('name', ''),
                        arguments=content_block.get('input', {})
                    )
                )

        return LLMResponse(
            text=response_text if response_text else None,
            tool_calls=tool_calls,
            raw=data
        )


class OpenAICompatibleProvider(LLMProvider):
    """پیاده‌سازی ارتباط با endpoint سازگار با OpenAI Chat Completions"""

    @staticmethod
    def _convert_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """تبدیل پیام‌های قالب بلوکی (tool_use / tool_result) به قالب OpenAI"""
        out: List[Dict[str, Any]] = []
        for msg in messages:
            content = msg.get('content')
            if not isinstance(content, list):
                out.append(msg)
                continue
            if msg['role'] == 'assistant':
                text = ''.join(b.get('text', '') for b in content if b.get('type') == 'text')
                calls = [{
                    'id': b['id'],
                    'type': 'function',
                    'function': {'name': b['name'], 'arguments': json.dumps(b.get('input', {}), ensure_ascii=False)},
                } for b in content if b.get('type') == 'tool_use']
                item: Dict[str, Any] = {'role': 'assistant', 'content': text or None}
                if calls:
                    item['tool_calls'] = calls
                out.append(item)
            else:
                for b in content:
                    if b.get('type') == 'tool_result':
                        out.append({'role': 'tool', 'tool_call_id': b['tool_use_id'], 'content': b.get('content', '')})
                    elif b.get('type') == 'text':
                        out.append({'role': 'user', 'content': b.get('text', '')})
        return out

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30
    ):
        self.api_key = api_key or conf.get('LLM_API_KEY')
        self.model = model or conf.get('LLM_MODEL') or 'gpt-4o-mini'
        self.base_url = (base_url or conf.get('LLM_BASE_URL') or '').rstrip('/')
        self.timeout = int(conf.get('LLM_TIMEOUT') or timeout)

    def complete(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        _require_url(self.base_url)
        url = f"{self.base_url}/chat/completions"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        openai_messages = []
        if system:
            openai_messages.append({'role': 'system', 'content': system})

        openai_messages.extend(self._convert_messages(messages))

        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': openai_messages,
            'stream': False,  # بعضی دروازه‌ها بدون این کلید پاسخ را استریم می‌کنند
        }
        if tools:
            payload['tools'] = tools

        resp = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
                continue
            if resp.status_code >= 500 and attempt < 2:
                logger.warning('Assistant LLM %s (تلاش %s): %s', resp.status_code, attempt + 1, resp.text[:300])
                time.sleep(1 + attempt)
                continue
            break
        if resp.status_code == 429:
            raise requests.HTTPError('محدودیت نرخ درخواست (Rate Limit)', response=resp)
        if resp.status_code >= 400:
            logger.error('Assistant LLM HTTP %s: %s', resp.status_code, resp.text[:500])
        resp.raise_for_status()

        data = resp.json()
        choice = data['choices'][0]['message']
        response_text = choice.get('content')

        tool_calls = []
        for tc in choice.get('tool_calls', []):
            try:
                args = json.loads(tc['function']['arguments'])
            except Exception:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc['id'],
                    name=tc['function']['name'],
                    arguments=args
                )
            )

        return LLMResponse(
            text=response_text,
            tool_calls=tool_calls,
            raw=data
        )


class MockProvider(LLMProvider):
    """ارائه‌دهنده تستی برای تست‌های واحد بدون شبکه"""

    def __init__(self, responses: Optional[List[LLMResponse]] = None):
        self.responses = list(responses or [])
        self.call_history: List[Dict[str, Any]] = []

    def complete(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        self.call_history.append({
            'messages': messages,
            'system': system,
            'tools': tools,
        })
        if self.responses:
            return self.responses.pop(0)
        return LLMResponse(text='پاسخ تست پیش‌فرض')


def get_llm_provider() -> LLMProvider:
    """ساخت ارائه‌دهنده مناسب بر اساس تنظیمات محیطی"""
    provider_type = str(conf.get('LLM_PROVIDER') or 'anthropic').strip().lower()
    base_url = str(conf.get('LLM_BASE_URL') or '').strip()

    if provider_type == 'openai' or (base_url and 'openai' in base_url):
        return OpenAICompatibleProvider()
    return AnthropicProvider()


def _backend_name(provider) -> str:
    return {'AnthropicProvider': 'anthropic', 'OpenAICompatibleProvider': 'openai', 'MockProvider': 'mock'}.get(type(provider).__name__, type(provider).__name__)


def _usage_tokens(raw) -> tuple:
    usage = (raw or {}).get('usage') or {}
    return (usage.get('input_tokens') or usage.get('prompt_tokens') or 0,
            usage.get('output_tokens') or usage.get('completion_tokens') or 0)


def _timed_complete(provider, trace, **kwargs):
    """provider.complete با ثبت لاگ مدل (مدت، توکن، ابزارهای درخواستی، خطا)"""
    started = time.time()
    try:
        response = provider.complete(**kwargs)
    except Exception as e:
        trace.model_call('chat', _backend_name(provider), getattr(provider, 'model', ''), ok=False,
                         ms=int((time.time() - started) * 1000), error=f'{type(e).__name__}: {e}')
        raise
    in_tok, out_tok = _usage_tokens(response.raw)
    trace.model_call('chat', _backend_name(provider), getattr(provider, 'model', ''), ok=True,
                     ms=int((time.time() - started) * 1000), input_tokens=in_tok, output_tokens=out_tok,
                     detail={'tools': [tc.name for tc in response.tool_calls], 'has_text': bool(response.text),
                             'offered': getattr(trace, 'tool_selection', 'all')})
    return response


def run_assistant_agent(
    user,
    conversation: AssistantConversation,
    user_prompt: str,
    provider: Optional[LLMProvider] = None,
    attachment: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """حلقه‌ی دستیار به‌همراه ثبت لاگ درخواست (مسیر، مدل‌ها، ابزارها، مدت)"""
    from agent_helper.trace import RequestTrace
    trace = RequestTrace(user, conversation, user_prompt)
    try:
        for event in _run_agent(user, conversation, user_prompt, provider, trace, attachment):
            if event.get('event') == 'error':
                trace.set_error(event.get('message'))
            elif event.get('event') == 'done':
                trace.path = event.get('path', 'llm')
            yield event
    except Exception as e:
        trace.set_error(f'{type(e).__name__}: {e}')
        raise
    finally:
        trace.finish()


def _today_line() -> str:
    if not conf.flag('TODAY_LINE'):
        return ''
    import jdatetime
    d = jdatetime.date.today()
    return f'\n\nتاریخ امروز (شمسی): {d.year:04d}-{d.month:02d}-{d.day:02d}'


def _run_agent(
    user,
    conversation: AssistantConversation,
    user_prompt: str,
    provider: Optional[LLMProvider],
    trace,
    attachment: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    حلقه کامل عامل هوشمند (Agent Loop)
    ارسال پیام‌ها + ابزارها، اجرای tool calls، و ارسال استریم رویدادهای SSE
    """
    if provider is None:
        provider = get_llm_provider()

    content = {'text': user_prompt}
    message_text = user_prompt  # متن خود کاربر (بدون متن استخراج‌شده از تصویر) برای انتخاب ابزارها
    if attachment:
        # تصویر پیوست: ابتدا استخراج اطلاعات؛ متن استخراج‌شده به پیام اضافه می‌شود تا در تاریخچه بماند
        from agent_helper import vision
        yield {'event': 'tool_status', 'status': 'در حال خواندن تصویر پیوست...'}
        try:
            extracted = vision.extract_document(attachment, trace=trace)
        except Exception as e:
            logger.exception('Vision extraction crashed: %s', e)
            extracted = {'text': '', 'error': 'خواندن تصویر انجام نشد.'}
        if extracted.get('error'):
            AssistantMessage.objects.create(conversation=conversation, role='user', content=content)
            yield {'event': 'error', 'message': extracted['error'] + ' لطفاً دوباره تلاش کنید یا اطلاعات را بنویسید.'}
            return
        user_prompt = user_prompt + extracted['text']
        content = {'text': user_prompt, 'attachment': attachment}
        if extracted.get('data') is not None:
            yield {'event': 'attachment_data', 'data': extracted['data'], 'warning': extracted.get('warning', '')}

    # ذخیره پیام کاربر در دیتابیس
    user_msg = AssistantMessage.objects.create(conversation=conversation, role='user', content=content)

    # مسیر سریع (مدل سبک + اجرای مستقیم ابزار)؛ اگر مطمئن نبود None و ادامه با LLM. با پیوست همیشه مسیر LLM
    from agent_helper.router import try_fast_path
    fast = None if attachment else try_fast_path(user, conversation, user_prompt, trace=trace)
    if fast is not None:
        for event in fast['events']:
            yield event
        assistant_msg = AssistantMessage.objects.create(
            conversation=conversation, role='assistant', content={'text': fast['text']})
        yield {'event': 'done', 'conversation_id': conversation.id, 'message_id': assistant_msg.id, 'path': 'fast'}
        return

    # بازسازی سابقه پیام‌های گفتگو
    previous_messages = AssistantMessage.objects.filter(
        conversation=conversation
    ).order_by('created_at')

    # قالب‌بندی پیام‌ها برای مدل
    llm_messages: List[Dict[str, Any]] = []
    for msg in previous_messages:
        if msg.role == 'user':
            llm_messages.append({'role': 'user', 'content': msg.content.get('text', '')})
        elif msg.role == 'assistant':
            # بازسازی محتوای چندبخشی در صورت وجود tool_use
            content = msg.content
            if 'blocks' in content:
                llm_messages.append({'role': 'assistant', 'content': content['blocks']})
            elif 'text' in content:
                llm_messages.append({'role': 'assistant', 'content': content['text']})
        elif msg.role == 'tool':
            llm_messages.append({
                'role': 'user',
                'content': [{
                    'type': 'tool_result',
                    'tool_use_id': msg.content.get('tool_call_id', ''),
                    'content': json.dumps(msg.content.get('result', {}), ensure_ascii=False)
                }]
            })

    # آماده‌سازی ابزارها: فقط ابزارها و قاعده‌های مرتبط با همین پیام (بدون سیگنال مطمئن: همه)
    from agent_helper.prompts import build_system_prompt
    from agent_helper.selection import select_tags, select_tools
    tags = select_tags(conversation, message_text, attachment, getattr(trace, 'classification', None))
    specs = select_tools(tags)
    trace.tool_selection = sorted(tags) if tags is not None else 'all'
    is_anthropic = isinstance(provider, AnthropicProvider) or isinstance(provider, MockProvider)
    tools = agent_tools.anthropic_schemas(specs) if is_anthropic else agent_tools.openai_schemas(specs)
    system_prompt = build_system_prompt(tags) + _today_line()

    final_text = ""
    iteration_count = 0

    try:
        max_iterations = int(conf.get('MAX_AGENT_ITERATIONS') or MAX_AGENT_ITERATIONS)
        while iteration_count < max_iterations:
            iteration_count += 1

            response = _timed_complete(
                provider, trace,
                messages=llm_messages,
                system=system_prompt,
                tools=tools
            )

            # متن همراه با فراخوانی ابزار (مثلاً «فرم را می‌گیرم…») به کاربر نشان داده نمی‌شود؛ فقط پاسخ نهایی
            if response.text and not response.tool_calls:
                final_text += response.text
                yield {'event': 'token', 'text': response.text}

            # اگر مدل هیچ ابزاری فراخوانی نکرد، حلقه پایان می‌یابد
            if not response.tool_calls:
                break

            # ثبت پیام assistant همراه با tool_use در تاریخچه
            assistant_blocks: List[Dict[str, Any]] = []
            if response.text:
                assistant_blocks.append({'type': 'text', 'text': response.text})

            for tc in response.tool_calls:
                assistant_blocks.append({
                    'type': 'tool_use',
                    'id': tc.id,
                    'name': tc.name,
                    'input': tc.arguments
                })

            llm_messages.append({'role': 'assistant', 'content': assistant_blocks})

            # اجرای ابزارها و جمع‌آوری نتایج
            tool_results_blocks: List[Dict[str, Any]] = []
            for tc in response.tool_calls:
                spec = agent_tools.registry.tool(tc.name)
                yield {'event': 'tool_status', 'status': spec.status_text(tc.arguments) if spec else f'در حال اجرای ابزار {tc.name}...'}

                proposed = []
                result = agent_tools.run_logged(trace, tc.name, tc.arguments, user, conversation, collect=proposed)

                # رویدادهای اختصاصی ابزار برای رابط کاربری (جدول، کارت وضعیت)
                if spec and spec.events and isinstance(result, dict):
                    for ev in spec.events(result):
                        yield ev
                # کارت اقدام معلق برای هر پیشنهادی که ابزار ساخت (از ActionKind.preview)
                for action in proposed:
                    yield pending_event(action)

                tool_results_blocks.append({
                    'type': 'tool_result',
                    'tool_use_id': tc.id,
                    'content': json.dumps(result, ensure_ascii=False)
                })

            llm_messages.append({'role': 'user', 'content': tool_results_blocks})

        # ثبت پاسخ نهایی دستیار در دیتابیس
        assistant_msg = AssistantMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content={'text': final_text}
        )

        yield {
            'event': 'done',
            'conversation_id': conversation.id,
            'message_id': assistant_msg.id,
            'path': 'llm'
        }

    except requests.Timeout:
        yield {
            'event': 'error',
            'message': 'زمان پاسخگویی سرویس مدل هوش مصنوعی به پایان رسید (Timeout). لطفاً دوباره تلاش کنید.'
        }
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500
        if status_code == 429:
            err_msg = 'سرویس هوش مصنوعی در حال حاضر شلوغ است (محدودیت نرخ درخواست). لطفاً کمی بعد تلاش کنید.'
        elif status_code in (401, 403):
            err_msg = 'خطای اعتبارسنجی کلید API سرویس هوش مصنوعی رخ داده است.'
        else:
            err_msg = 'خطایی در ارتباط با سرور هوش مصنوعی رخ داد. لطفاً مجدداً امتحان کنید.'
        event = {'event': 'error', 'message': err_msg}
        if settings.DEBUG:
            event['detail'] = f'HTTP {status_code}: {(e.response.text[:300] if e.response is not None else "")}'
        yield event
    except requests.RequestException:
        yield {
            'event': 'error',
            'message': 'امکان برقراری ارتباط با ارائه‌دهنده سرویس هوش مصنوعی میسر نشد.'
        }
    except Exception as e:
        logger.exception("Unexpected error in run_assistant_agent: %s", str(e))
        yield {
            'event': 'error',
            'message': 'خطای غیرمنتظره‌ای در پردازش درخواست رخ داد.'
        }

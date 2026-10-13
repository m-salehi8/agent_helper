# agent-helper

هسته‌ی عمومی یک دستیار گفتگومحور برای Django: حلقه‌ی LLM با ابزار، مسیر سریع بدون LLM (regex + Jev یا مدل لوکال)،
اقدام‌های معلقی که فقط با دکمه‌ی خود کاربر اجرا می‌شوند، خواندن تصویر پیوست، لاگ درخواست/مدل/ابزار، سقف نرخ و
استریم SSE. هر دامنه (سفارش، یادداشت، درخواست‌های اداری، …) یک **افزونه** است.

## اصول غیرقابل‌تغییر
1. ابزارها همیشه با `request.user` اجرا می‌شوند؛ شناسه‌ی کاربر هرگز از ورودی مدل خوانده نمی‌شود.
2. هیچ ابزار «اجرایی» وجود ندارد: ابزار فقط می‌خواند یا با `ctx.propose()` یک `PendingAction` می‌سازد.
   اجرا فقط در `POST actions/<id>/confirm/` است: قفل ردیف، مالکیت، مهلت (پیش‌فرض ۱۰ دقیقه)، idempotent، ممیزی.
3. مسیر سریع فقط با اطمینان ≥ آستانه؛ هر خطا یا تردید ⇒ LLM.
4. هیچ نشانی پیش‌فرضی به اینترنت اشاره نمی‌کند؛ LLM، Jev و مدل بینایی فقط با URL قابل تنظیم.

## نصب (آفلاین)
```bash
pip install --no-index --find-links wheelhouse agent-helper agent-helper-demo
```
وابستگی‌ها: Django ≥ 4.2، djangorestframework، django-jalali، jdatetime، requests.

```python
# settings.py
INSTALLED_APPS += ['rest_framework', 'django_jalali', 'agent_helper', 'agent_helper_demo']
AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',                       # openai = هر سرور سازگار با OpenAI (vLLM، llama.cpp، …)
    'LLM_BASE_URL': 'http://llm.internal:8000/v1',
    'LLM_MODEL': 'qwen3',
}

# urls.py
urlpatterns += [path('api/assistant/', include('agent_helper.urls'))]
```
```bash
python manage.py migrate
```

## API
| روش و مسیر | کار |
|---|---|
| `POST chat/` | `{"message", "conversation_id"?, "image"?: data-URL}` ⇒ استریم SSE |
| `POST actions/<id>/confirm/` | اجرای اقدام معلق؛ بدنه به `ActionKind.execute` داده می‌شود |
| `POST actions/<id>/cancel/` | لغو |
| `GET conversations/`، `conversations/<id>/` | گفتگوهای خود کاربر |

رویدادهای SSE: `token`، `tool_status`، `pending_action`، `done` (با `path`: fast یا llm)، `error`، `attachment_data`
و هر رویدادی که `ToolSpec.events` افزونه‌ها بسازند.

## تنظیمات
هر کلید به این ترتیب خوانده می‌شود: `settings.AGENT_HELPER[key]` ← متغیر محیطی ← پیش‌فرض.

| کلید | متغیر محیطی | پیش‌فرض |
|---|---|---|
| `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_TIMEOUT` | `ASSISTANT_LLM_*` | `anthropic` / — / — / — / 30 |
| `MAX_AGENT_ITERATIONS` | — | 6 |
| `USE_FAST_ROUTER` | `ASSISTANT_USE_FAST_ROUTER` | خاموش (`1` = روشن) |
| `FAST_THRESHOLD` | `ASSISTANT_FAST_THRESHOLD` | 0.8 |
| `INTENT_BACKEND` (`jev` یا `llm`) / `INTENT_TIMEOUT` | `ASSISTANT_INTENT_*` | `jev` / 4 |
| `INTENT_BASE_URL` / `INTENT_API_KEY` / `INTENT_MODEL` | `ASSISTANT_INTENT_*` | همان LLM |
| `JEV_BASE_URL` / `JEV_API_KEY` / `JEV_MODEL` | `TYPESAFE_*` | — / — / `jev-1.13.0` |
| `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` / `VISION_TIMEOUT` | `ASSISTANT_VISION_*` | همان LLM / 90 |
| `UPLOAD_DIR` / `MAX_UPLOAD_BYTES` | — | `assistant_uploads` / ۵ مگابایت |
| `PER_MINUTE_LIMIT` / `DAILY_LIMIT` | — | 30 / `settings.ASSISTANT_DAILY_LIMIT` یا 100 |
| `ACTION_EXPIRES_MINUTES` | — | 10 |
| `TOOL_SELECTION` (`auto` یا `all`) | `ASSISTANT_TOOL_SELECTION` | `auto` |
| `REGISTER_ADMIN` / `ADMIN_BASE` / `ADMIN_INLINE_BASE` | — | True / کلاس‌های admin جنگو |
| `ASSISTANT_TITLE` / `ASSISTANT_MISSION` | — | هویت پرامپت (افزونه هم می‌تواند بدهد) |
| `TODAY_LINE` | — | True (تاریخ شمسی امروز در انتهای پرامپت) |
| `TEST_USER_FACTORY` | — | مسیر تابع ساخت کاربر در تست‌ها (برای مدل کاربر خاص) |

`TOOL_SELECTION='auto'`: به LLM فقط ابزارها و قاعده‌های پرامپتی داده می‌شود که برچسبشان با پیام جور است (حالت گفتگو،
پیوست، regex مسیرها، پاسخ مدل سبک، ابزارهای قبلی همین گفتگو). بدون سیگنال مطمئن: همه.

## نوشتن افزونه
```python
# myplugin/apps.py
from django.apps import AppConfig

class MyPluginConfig(AppConfig):
    name = 'myplugin'

    def ready(self):
        import agent_helper
        from myplugin.plugin import PLUGIN
        agent_helper.register(PLUGIN)
```
```python
# myplugin/plugin.py
from agent_helper import actions
from agent_helper.plugins import ActionKind, FastRoute, Plugin, PromptFragment, ToolSpec

def list_items(user, args, ctx):                 # فقط خواندن، فقط داده‌ی user
    return {'items': [...]}

def propose_thing(user, args, ctx):              # فقط پیشنهاد
    action = ctx.propose('do_thing', {'x': args['x']})
    return {'status': 'ready', 'action_id': action.id}

def execute_thing(user, action, params):         # فقط از confirm، داخل تراکنش
    ...
    actions.audit(user, action, 'confirmed', 'انجام شد')
    return {'status': 'confirmed', 'message': 'انجام شد', 'results': [...], 'status_code': 200}

PLUGIN = Plugin(
    name='my',
    tools=[
        ToolSpec('list_items', 'توضیح برای مدل', {'type': 'object', 'properties': {}}, list_items, tags=('items',)),
        ToolSpec('propose_thing', '…', {'type': 'object', 'properties': {'x': {'type': 'string'}}, 'required': ['x']},
                 propose_thing, read_only=False, proposes='do_thing', tags=('items',)),
    ],
    actions=[ActionKind('do_thing', execute=execute_thing, preview=lambda p: {'kind': 'do_thing', 'x': p['x']},
                        propose_schema={'type': 'object', 'required': ['x']})],
    prompt_fragments=[PromptFragment('قاعده‌ی دامنه …', order=60, tags=('items',))],
    fast_routes=[FastRoute('items', handler=lambda req: req.reply('…'), guard=lambda t: 'فهرست' in t, tags=('items',))],
)
```
- `ToolSpec`: `handler(user, args, ctx) -> dict`؛ `read_only=False` فقط با `proposes`؛ `status` و `events` برای SSE؛
  `conversation_mode` برای گفتگوهای چندمرحله‌ای.
- `ActionKind`: `execute(user, action, params)` با خروجی `status` (confirmed/partial/failed/cancelled) یا
  `error` + `status_code` برای رد درخواست (اقدام pending می‌ماند)؛ وضعیت و نتیجه را هسته ذخیره می‌کند.
- `CatalogProvider`: موجودیت‌هایی که کاربر با نام صدا می‌زند؛ سؤال «کدام؟» در Jev و تطبیق متنی از آن ساخته می‌شود.
- `PromptFragment`: قاعده‌های دامنه؛ هم‌کلید با قاعده‌ی هسته (`identity`، `rule.ambiguity`، `rule.injection`، `rule.scope`) جایگزینش می‌کند.
- `FastRoute`: مسیر دروازه (`guard` و/یا `gate_question` بله/خیر) یا مسیر اصلی (`questions` + `handler`)؛ خروجی
  `req.reply(...)`، `Defer('reason')` یا `None`.

نمونه‌ی کامل: پکیج `agent-helper-demo`.

## نصب روی استقراری که جدول‌ها را با برچسب دیگری دارد
```python
# myproject/agent_apps.py
from agent_helper.apps import AgentHelperConfig
class AssistantConfig(AgentHelperConfig):
    label = 'my_old_label'       # همان جدول‌ها، content typeها و نام URLهای ادمین موجود

INSTALLED_APPS += ['myproject.agent_apps.AssistantConfig']
MIGRATION_MODULES = {'my_old_label': 'myproject.old_migrations'}   # تاریخچه‌ی migration موجود
```

## تست
```bash
python manage.py test agent_helper
```

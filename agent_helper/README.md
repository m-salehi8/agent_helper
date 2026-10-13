# agent-helper

> **Beta (0.1.0b1)** — not a stable release yet; the API and settings may change before 1.0.
> Install with `--pre` or pin the exact version. [فارسی](README.fa.md)

The generic core of a conversational assistant for Django: an LLM tool loop, a no-LLM fast path (regex + Jev or a
local model), pending actions that run only when the user presses the button, image attachments, request/model/tool
logs, rate limits and SSE streaming. Every domain (orders, notes, office requests, …) is a **plugin**.

Full documentation (HTML, English and Persian) ships inside the package: `agent_helper/docs/en/index.html`
(source in `docs_src/`, built with `python docs_src/build.py`).

## Invariants
1. Tools always run with `request.user`; a user id is never read from model output.
2. There is no "executing" tool: a tool only reads, or creates a `PendingAction` with `ctx.propose()`.
   Execution happens only in `POST actions/<id>/confirm/`: row lock, ownership, expiry (10 minutes by default),
   idempotency, audit.
3. The fast path answers only with confidence ≥ threshold; any error or doubt ⇒ LLM.
4. No default address points to the internet; the LLM, Jev and the vision model are configured by URL only.

## Install (offline)
```bash
pip install --no-index --find-links wheelhouse --pre agent-helper agent-helper-demo
```
Dependencies: Django ≥ 4.2, djangorestframework, django-jalali, jdatetime, requests.

```python
# settings.py
INSTALLED_APPS += ['rest_framework', 'django_jalali', 'agent_helper', 'agent_helper_demo']
AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',                       # openai = any OpenAI-compatible server (vLLM, llama.cpp, …)
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
| Method and path | Purpose |
|---|---|
| `POST chat/` | `{"message", "conversation_id"?, "image"?: data-URL}` ⇒ SSE stream |
| `POST actions/<id>/confirm/` | Execute a pending action; the body is passed to `ActionKind.execute` |
| `POST actions/<id>/cancel/` | Cancel |
| `GET conversations/`, `conversations/<id>/` | The user's own conversations |

SSE events: `token`, `tool_status`, `pending_action`, `done` (with `path`: fast or llm), `error`, `attachment_data`
and any event a plugin's `ToolSpec.events` produces.

## Settings
Each key is resolved as: `settings.AGENT_HELPER[key]` → environment variable → default.

| Key | Environment variable | Default |
|---|---|---|
| `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_TIMEOUT` | `ASSISTANT_LLM_*` | `anthropic` / — / — / — / 30 |
| `MAX_AGENT_ITERATIONS` | — | 6 |
| `USE_FAST_ROUTER` | `ASSISTANT_USE_FAST_ROUTER` | off (`1` = on) |
| `FAST_THRESHOLD` | `ASSISTANT_FAST_THRESHOLD` | 0.8 |
| `INTENT_BACKEND` (`jev` or `llm`) / `INTENT_TIMEOUT` | `ASSISTANT_INTENT_*` | `jev` / 4 |
| `INTENT_BASE_URL` / `INTENT_API_KEY` / `INTENT_MODEL` | `ASSISTANT_INTENT_*` | same as the LLM |
| `JEV_BASE_URL` / `JEV_API_KEY` / `JEV_MODEL` | `TYPESAFE_*` | — / — / `jev-1.13.0` |
| `VISION_BASE_URL` / `VISION_API_KEY` / `VISION_MODEL` / `VISION_TIMEOUT` | `ASSISTANT_VISION_*` | same as the LLM / 90 |
| `UPLOAD_DIR` / `MAX_UPLOAD_BYTES` | — | `assistant_uploads` / 5 MB |
| `PER_MINUTE_LIMIT` / `DAILY_LIMIT` | — | 30 / `settings.ASSISTANT_DAILY_LIMIT` or 100 |
| `ACTION_EXPIRES_MINUTES` | — | 10 |
| `TOOL_SELECTION` (`auto` or `all`) | `ASSISTANT_TOOL_SELECTION` | `auto` |
| `REGISTER_ADMIN` / `ADMIN_BASE` / `ADMIN_INLINE_BASE` | — | True / Django admin classes |
| `ASSISTANT_TITLE` / `ASSISTANT_MISSION` | — | prompt identity (a plugin can also provide it) |
| `TODAY_LINE` | — | True (today's Jalali date at the end of the prompt) |
| `TEST_USER_FACTORY` | — | dotted path of the user factory used in tests (for a custom user model) |

`TOOL_SELECTION='auto'`: only the tools and prompt rules whose tags match the message are sent to the LLM (conversation
mode, attachment, route regexes, light-model answers, tools already used in the conversation). No confident signal: all.

## Writing a plugin
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

def list_items(user, args, ctx):                 # read only, only user's data
    return {'items': [...]}

def propose_thing(user, args, ctx):              # proposal only
    action = ctx.propose('do_thing', {'x': args['x']})
    return {'status': 'ready', 'action_id': action.id}

def execute_thing(user, action, params):         # only from confirm, inside a transaction
    ...
    actions.audit(user, action, 'confirmed', 'done')
    return {'status': 'confirmed', 'message': 'Done.', 'results': [...], 'status_code': 200}

PLUGIN = Plugin(
    name='my',
    tools=[
        ToolSpec('list_items', 'Description for the model', {'type': 'object', 'properties': {}}, list_items, tags=('items',)),
        ToolSpec('propose_thing', '…', {'type': 'object', 'properties': {'x': {'type': 'string'}}, 'required': ['x']},
                 propose_thing, read_only=False, proposes='do_thing', tags=('items',)),
    ],
    actions=[ActionKind('do_thing', execute=execute_thing, preview=lambda p: {'kind': 'do_thing', 'x': p['x']},
                        propose_schema={'type': 'object', 'required': ['x']})],
    prompt_fragments=[PromptFragment('Domain rule …', order=60, tags=('items',))],
    fast_routes=[FastRoute('items', handler=lambda req: req.reply('…'), guard=lambda t: 'list' in t, tags=('items',))],
)
```
- `ToolSpec`: `handler(user, args, ctx) -> dict`; `read_only=False` only with `proposes`; `status` and `events` for SSE;
  `conversation_mode` for multi-step dialogs.
- `ActionKind`: `execute(user, action, params)` returns a `status` (confirmed/partial/failed/cancelled), or
  `error` + `status_code` to reject the request (the action stays pending); the core stores the status and result.
- `CatalogProvider`: entities the user refers to by name; the "which one?" Jev question and text matching are built from it.
- `PromptFragment`: domain rules; using the key of a core rule (`identity`, `rule.ambiguity`, `rule.injection`, `rule.scope`) replaces it.
- `FastRoute`: a gate route (`guard` and/or a yes/no `gate_question`) or a main route (`questions` + `handler`); returns
  `req.reply(...)`, `Defer('reason')` or `None`.

Complete example: the `agent-helper-demo` package.

## Installing where the tables exist under another label
```python
# myproject/agent_apps.py
from agent_helper.apps import AgentHelperConfig
class AssistantConfig(AgentHelperConfig):
    label = 'my_old_label'       # same tables, content types and admin URL names

INSTALLED_APPS += ['myproject.agent_apps.AssistantConfig']
MIGRATION_MODULES = {'my_old_label': 'myproject.old_migrations'}   # the existing migration history
```

## Tests
```bash
python manage.py test agent_helper
```

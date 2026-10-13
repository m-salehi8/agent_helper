from lib import adm, code, page, table


def security():
    body = '''
<h2>Invariants</h2>
<ol>
<li><b>User scope:</b> tools always run with <code>request.user</code>; the core never reads a user id from model output and tools must not either.</li>
<li><b>Proposal separate from execution:</b> there is no "executing" tool. A non-read-only tool must have <code>proposes</code> and may only create a PendingAction.</li>
<li><b>Execution only by button:</b> <code>confirm</code> with a <code>select_for_update</code> lock, ownership, status and expiry checks; idempotent; inside a savepoint; audited.</li>
<li><b>Conservative fast path:</b> only with confidence ≥ threshold; a light-model or LLM error never produces a confident wrong answer.</li>
<li><b>No internet defaults:</b> every address comes from settings.</li>
</ol>
<h2>Threats and defences</h2>
''' + table(['Threat', 'Defence'], [
        ['A user asks for another user\'s data ("Mr X\'s orders")', 'Tools only return <code>user</code>\'s data; the model has no tool for another user'],
        ['Prompt injection in the message or data ("forget previous instructions")', 'The <code>rule.injection</code> rule; even if the model is fooled, there is no executing tool'],
        ['The model claims something was done', 'Prompt rules + real execution only in the button endpoint'],
        ["Confirming another user's action", 'Ownership check ⇒ 403'], ['Repeated / concurrent confirm', 'Row lock + idempotency'],
        ['Data changed between proposal and confirm', '<code>execute</code> re-checks (e.g. the amount)'],
        ['Stale proposal', 'Expiry (10 minutes by default) ⇒ <code>expired</code>'],
        ['Volume abuse', 'Per-minute and daily limits per user'], ['Malicious file', 'Only png/jpg/webp images, with a size limit'],
    ]) + '''
<h2>Plugin review checklist</h2>
<ul><li>Is every tool query filtered by <code>user</code>?</li><li>Is there no <code>save()</code>/<code>create()</code>/<code>delete()</code> in tool handlers?</li>
<li>Does <code>execute</code> re-validate the payload and trust <code>params</code> only as a selection from that payload?</li>
<li>Is <code>actions.audit</code> written for every executed item?</li><li>Do you have tests for "other user ⇒ 403" and "a proposal saves nothing"?</li></ul>
''' + adm('note', 'Logs and privacy', '<p>Message text (truncated to 1000 characters) and tool arguments are logged. If you handle sensitive data, restrict admin access to the logs and plan periodic cleanup.</p>')
    return page('security', 'Security model', 'Invariants, threats and the plugin review checklist', body)


def observability():
    body = '''
<h2>Logs</h2>
''' + table(['Model', 'One row per', 'Key fields'], [
        ['<code>AssistantRequestLog</code>', 'User message', '<code>path</code> (fast/llm/error), <code>fast_reason</code>, <code>intent</code>, <code>intent_confidence</code>, call counts, tokens, <code>duration_ms</code>, <code>error</code>'],
        ['<code>ModelCallLog</code>', 'Model call', '<code>kind</code> (intent/chat/vision), <code>model</code>, <code>ok</code>, <code>attempts</code>, tokens, duration, <code>detail</code> (light-model answers or requested tools and <code>offered</code>)'],
        ['<code>ToolCallLog</code>', 'Tool run', '<code>name</code>, <code>arguments</code>, <code>ok</code>, <code>result_summary</code>, duration'],
        ['<code>ActionAuditLog</code>', 'Real execution', 'User, action, item id, amount, status, detail'],
    ]) + '''
<p>Logging never breaks a response; a failure to store a log is only a warning in the logger.</p>
<h2>Reasons for falling back to the LLM (<code>fast_reason</code>)</h2>
''' + table(['Value', 'Meaning'], [
        ['<code>disabled</code>', 'The fast path is off'], ['<code>&lt;mode&gt;_dialog</code>', 'The conversation is in a multi-step mode'],
        ['<code>&lt;route&gt;_request</code>', 'A gate without a handler (always LLM)'], ['<code>classifier_error</code>', 'The light model was unavailable or timed out'],
        ['<code>a_or_b_ambiguous</code>', 'Two gates were confident at once'], ['<code>no_route</code>', 'No route answered'],
        ['Other', 'The reason a plugin gave with <code>Defer</code> (e.g. <code>low_intent_confidence</code>)'],
    ]) + '''
<h2>Admin</h2>
<p>All models are registered in the admin (read-only). Above the request log table a summary of the current filter is shown: fast-path share, average duration per path and total tokens.</p>
''' + code('''
AGENT_HELPER = {'ADMIN_BASE': 'myproject.admin.BaseModelAdmin', 'ADMIN_INLINE_BASE': 'myproject.admin.BaseTabularInline'}
''') + '''
<h2>Suggested monitoring metrics</h2>
''' + code('''
from django.db.models import Avg, Count, Q, Sum
from agent_helper.models import AssistantRequestLog

AssistantRequestLog.objects.filter(created_at__gte=since).aggregate(
    total=Count('id'), fast=Count('id', filter=Q(path='fast')), errors=Count('id', filter=Q(status='error')),
    avg_llm_ms=Avg('duration_ms', filter=Q(path='llm')), tokens=Sum('input_tokens') + Sum('output_tokens'))

AssistantRequestLog.objects.values('fast_reason').annotate(n=Count('id')).order_by('-n')[:10]
''') + '''
<ul><li>Fast-path to LLM ratio and the common fallback reasons.</li><li>Model error rate (<code>ModelCallLog.ok=False</code>).</li>
<li>Average tokens on the LLM path (effect of tool selection).</li><li>Expired actions (proposals the user did not confirm).</li></ul>
'''
    return page('observability', 'Logs, admin and monitoring', 'What is recorded and how to look at it', body)


def testing():
    body = '''
<h2>Test helpers</h2>
''' + table(['Helper', 'Purpose'], [
        ['<code>agent_helper.registry.override([PLUGIN])</code>', 'Only the given plugins are registered'],
        ['<code>agent_helper.llm.MockProvider([LLMResponse(...), ...])</code>', 'Fake LLM without network; <code>call_history</code> keeps the requests'],
        ['<code>agent_helper.testing.fast_router(on=True, **env)</code>', 'Turn the fast path on/off inside a block'],
        ['<code>mock.patch(\'agent_helper.nlu.classify\', return_value=...)</code>', 'Fake light-model answers'],
        ['<code>agent_helper.testing.make_user(name)</code>', 'Create a user (customisable with <code>TEST_USER_FACTORY</code>)'],
    ]) + '''
<h2>Agent loop</h2>
''' + code('''
from agent_helper.llm import LLMResponse, MockProvider, ToolCall, run_assistant_agent

provider = MockProvider([
    LLMResponse(tool_calls=[ToolCall(id='1', name='list_orders', arguments={})]),
    LLMResponse(text='You have two orders.'),
])
with override([PLUGIN]), fast_router(on=False):
    events = list(run_assistant_agent(user, conversation, 'my orders', provider=provider))

assert events[-1]['event'] == 'done'
assert len(provider.call_history[0]['tools']) == 2          # tools the model saw
''') + '''
<h2>Fast path</h2>
''' + code('''
from unittest import mock
from agent_helper import router

answers = {'intent': {'choice': 'list', 'confidence': 0.95}}
with override([PLUGIN]), fast_router(), mock.patch('agent_helper.nlu.classify', return_value=answers):
    res = router.try_fast_path(user, None, 'show my orders')
assert res['path'] == 'fast'
''') + '''
<h2>Pending action and endpoint</h2>
''' + code('''
from rest_framework.test import APIRequestFactory, force_authenticate
from agent_helper import actions
from agent_helper.views import ActionConfirmView

action = actions.create_pending(user, None, 'cancel_order', {'order_id': order.id})
req = APIRequestFactory().post(f'/api/assistant/actions/{action.id}/confirm/', {}, format='json')
force_authenticate(req, user=other_user)
assert ActionConfirmView.as_view()(req, action_id=action.id).status_code == 403
''') + '''
<h2>Running</h2>
''' + code('''
python manage.py test agent_helper myplugin
# the standalone example project (no other plugin installed):
cd agent_helper_demo && python manage.py test agent_helper agent_helper_demo
''', 'bash') + adm('tip', 'Isolation test', '<p>The core has a test that forbids imports from domain packages. For your own plugin, write tests for "a proposal saves nothing", "other user ⇒ 403" and "a repeated confirm executes once".</p>')
    return page('testing', 'Testing', 'Testing a plugin without network: MockProvider, override, fast path and endpoints', body)


def deployment():
    body = '''
<h2>Checklist</h2>
<ul><li>Wheels and the <code>wheelhouse</code> on the server; <code>pip install --no-index --pre</code>.</li>
<li><code>migrate</code>.</li><li>LLM, light-model and vision addresses in settings or environment variables.</li>
<li>A shared cache (Redis) for rate limits across processes.</li><li>nginx: no buffering for the <code>chat/</code> path; read timeout ≥ 120 seconds.</li>
<li>An ASGI/WSGI server with enough workers: each LLM conversation holds a worker until the stream ends.</li></ul>
''' + code('''
location /api/assistant/chat/ {
    proxy_pass http://app;
    proxy_buffering off;
    proxy_read_timeout 180s;
}
''', 'text') + '''
<h2>Self-hosted models</h2>
<ul><li><b>LLM:</b> vLLM or any OpenAI-compatible server with tool calling; <code>LLM_PROVIDER='openai'</code>. Prefix caching makes the repeated prompt tokens cheap.</li>
<li><b>Light model:</b> Jev (or any server with the same <code>/v1/systemone</code> contract) or a small model with logprobs (<code>INTENT_BACKEND='llm'</code>).</li>
<li><b>Vision:</b> a VL model on the same server or a separate one (<code>VISION_*</code>).</li></ul>
<p>After changing a model, re-run the routing evaluation and one full scenario per plugin.</p>
<h2>Installing on existing tables (different label)</h2>
<p>If the tables already exist from an earlier version under another app label (e.g. <code>assistant</code>), without changing the database:</p>
''' + code('''
# myproject/agent_apps.py
from agent_helper.apps import AgentHelperConfig

class AssistantConfig(AgentHelperConfig):
    name = 'agent_helper'
    label = 'my_old_label'      # same tables, content types, permissions and admin URL names

# settings.py
INSTALLED_APPS += ['myproject.agent_apps.AssistantConfig']
MIGRATION_MODULES = {'my_old_label': 'myproject.old_migrations'}   # the existing migration history
''') + adm('warn', 'Manual migrations', "<p>In this setup <code>makemigrations</code> must only run for the old label. The package's own initial migration (<code>agent_helper/migrations</code>) is for fresh installs.</p>") + '''
<h2>Upgrading</h2>
''' + code('''
pip install --no-index --find-links dist --pre --upgrade agent-helper
python manage.py migrate
python manage.py check
''', 'bash')
    return page('deployment', 'Deployment', 'Installing on an offline server, nginx, self-hosted models and installing on existing tables', body)


def troubleshooting():
    rows = [
        ['Every answer is "could not connect to the provider"', '<code>LLM_BASE_URL</code> is not set or the server is unreachable'],
        ['"An error occurred while talking to the AI server"', 'An HTTP error from the model server; see <code>ModelCallLog.error</code> (e.g. 410 deprecated model, 503 quota)'],
        ['Empty LLM answer or broken JSON', 'Some gateways stream without <code>stream: false</code>; the core sends it explicitly. The model must support tool calling'],
        ['The fast path never runs', '<code>USE_FAST_ROUTER</code>, <code>JEV_BASE_URL</code>/<code>JEV_API_KEY</code>; <code>fast_reason</code> in the log says why'],
        ['<code>agent_helper.E001</code> in check', 'A tool has <code>proposes</code> whose ActionKind is not registered'],
        ['ValueError "action kind … is not registered"', '<code>ctx.propose</code> with a wrong kind, or the plugin defining the action is not installed'],
        ['No action card appears', 'The tool must use <code>ctx.propose</code> (not create a PendingAction directly)'],
        ['Confirm returns 400 "expired"', 'The deadline passed; <code>expires_minutes</code> or <code>ACTION_EXPIRES_MINUTES</code>'],
        ['The stream arrives all at once', 'Proxy buffering; <code>proxy_buffering off</code>'],
        ['The model guesses values', 'Weak model; make the domain prompt rule more explicit and keep validation in the tool (the confirm card is the last barrier)'],
        ['The model lacks a needed tool', '<code>TOOL_SELECTION=\'all\'</code> or fix tags/<code>intent_tags</code>; check <code>ModelCallLog.detail.offered</code>'],
        ['429 from chat', 'User rate limit; <code>PER_MINUTE_LIMIT</code> and <code>DAILY_LIMIT</code>'],
    ]
    body = table(['Symptom', 'Cause and fix'], rows) + '''
<h2>FAQ</h2>
<h3>Does it work without the fast path?</h3><p>Yes; every message goes to the LLM. The fast path is only an optimisation.</p>
<h3>Can the model be changed per message?</h3><p><code>run_assistant_agent(..., provider=...)</code> accepts any provider; the default view reads it from settings.</p>
<h3>Is Persian required?</h3><p>The core rules and user-facing messages are in Persian; replace the <code>identity</code> and <code>rule.*</code> keys to change the prompt language. Dates are Jalali (django-jalali).</p>
<h3>How much conversation history does the model get?</h3><p>All user and assistant messages of the same conversation; tool outputs of earlier turns are not stored, so the model calls the tool again when needed.</p>
<h3>Is it production ready?</h3><p>Not yet: this is a beta (<code>0.1.0b1</code>). It is tested end to end, but the API may change before 1.0; pin the exact version.</p>
'''
    return page('troubleshooting', 'Troubleshooting and FAQ', 'Common errors and fixes', body)


def changelog():
    body = '''
<h2>0.1.0b1 — beta</h2>
<ul><li>First beta pre-release; not yet a stable release. The API and settings may change before 1.0.</li>
<li>Documentation in English and Persian, shipped inside the wheel.</li>
<li>Version string follows PEP 440 (<code>agent_helper.__version__</code>); install with <code>--pre</code> or an exact pin.</li></ul>
<h2>0.1.0 (internal)</h2>
<ul><li>First generic version.</li>
<li>Plugin contract: <code>ToolSpec</code>, <code>ActionKind</code>, <code>CatalogProvider</code>, <code>PromptFragment</code>, <code>FastRoute</code>, <code>Plugin</code>.</li>
<li>Generic pending actions: preview from <code>ActionKind.preview</code>, status stored by the core, execution errors audited.</li>
<li>Generic fast path with Jev questions from plugins; a local-model backend.</li>
<li>Selection of tools and rules relevant to the message (<code>TOOL_SELECTION</code>).</li>
<li><code>AGENT_HELPER</code> settings with environment-variable support; no internet defaults.</li>
<li>Example plugin <code>agent-helper-demo</code> with a standalone project.</li></ul>
'''
    return page('changelog', 'Changelog', 'Version history', body)

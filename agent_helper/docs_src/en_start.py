from lib import adm, code, page, table


def index():
    body = '''
<p><b>agent-helper</b> is a Django app for building a conversational assistant on top of your own system's data. The core
knows nothing about any domain; every use case (orders, notes, office requests, …) is a <b>plugin</b> that registers its own
tools, actions and rules.</p>
<div class="cards">
<a href="tutorial.html"><b>🚀 Quick start</b><span>From an empty Django project to the first chat in 10 minutes</span></a>
<a href="plugins.html"><b>🧩 Writing a plugin</b><span>Tools, pending actions, fast routes and prompt rules</span></a>
<a href="http-api.html"><b>📡 API and SSE</b><span>Endpoints, events, request and response samples</span></a>
<a href="security.html"><b>🛡️ Security model</b><span>Why the model never executes anything on its own</span></a>
</div>
<h2>What you get</h2>
<ul>
<li><b>Agent loop with tools</b> on any OpenAI-compatible server (vLLM, llama.cpp, …) or Anthropic; at most 6 rounds.</li>
<li><b>Fast path without the LLM:</b> regex plus one call to a light model (Jev, or a local model with logprobs) for frequent messages; any doubt ⇒ LLM.</li>
<li><b>Pending actions:</b> the model only creates a <i>proposal</i>; execution happens only when the user presses the button, with a lock, an expiry, idempotency and an audit trail.</li>
<li><b>SSE streaming</b> for text, tool status, cards and errors.</li>
<li><b>Image attachments</b> (e.g. an invoice) read by a vision model, with arithmetic checks.</li>
<li><b>Full logging:</b> every message, model call and tool call with timing and tokens; admin included.</li>
<li><b>Token reduction:</b> only the tools and rules relevant to the message are sent to the model.</li>
<li><b>Rate limits</b> per minute and per day for each user.</li>
<li><b>Offline:</b> no default address points to the internet; everything is configured by URL.</li>
</ul>
<h2>At a glance</h2>
''' + code('''
# myplugin/plugin.py
from agent_helper.plugins import Plugin, ToolSpec

def list_orders(user, args, ctx):
    return {'orders': [{'id': o.id, 'total': o.total} for o in user.orders.all()[:20]]}

PLUGIN = Plugin(name='orders', tools=[
    ToolSpec('list_orders', "List the user's orders", {'type': 'object', 'properties': {}}, list_orders),
])
''') + '''
<p>The user writes "show my orders", the model calls the <code>list_orders</code> tool (always for <code>request.user</code>) and the answer is streamed to the UI as SSE.</p>
<h2>Packages</h2>
''' + table(['Package', 'Role'], [
        ['<code>agent-helper</code>', 'The core (this documentation)'],
        ['<code>agent-helper-demo</code>', 'Example "notes and leave" plugin with a standalone project; the best place to start reading code'],
    ]) + '''
<h2>Requirements</h2>
<ul><li>Python ≥ 3.10, Django ≥ 4.2, Django REST framework ≥ 3.14</li><li>django-jalali and jdatetime (Jalali dates), requests</li>
<li>An LLM server with tool calling support (for the LLM path)</li><li>Optional: Jev or a local model with logprobs for the fast path; a vision model for image attachments</li></ul>
'''
    return page('index', 'agent-helper', 'A pluggable assistant for Django: an LLM with tools, a no-LLM fast path, and actions that only the user executes', body)


def installation():
    body = '''
<h2>Install from wheels (offline)</h2>
<p>Production servers often have no internet access; prepare the wheels and dependencies on a development machine and carry them over.</p>
<ol class="steps">
<li><b>Build the package wheels</b> (no internet needed):''' + code('''
cd packages
pip wheel --no-deps --no-build-isolation --no-index -w dist ./agent_helper ./agent_helper_demo
''', 'bash') + '''</li>
<li><b>Collect dependencies</b> (once, on a machine with access):''' + code('''
pip download --only-binary=:all: -d wheelhouse \\
    Django==5.0.4 djangorestframework==3.15.1 django-jalali==6.2.1 jdatetime==5.0.0 requests==2.32.3
''', 'bash') + '''</li>
<li><b>Install on the server:</b>''' + code('''
pip install --no-index --find-links wheelhouse --find-links dist --pre agent-helper
''', 'bash') + '''</li></ol>
''' + adm('note', 'Beta version', '<p>The current release is a pre-release (<code>0.1.0b1</code>), so pip only picks it with <code>--pre</code> or an exact pin such as <code>agent-helper==0.1.0b1</code>.</p>') + adm('tip', 'Versions', '<p>The versions above are the tested ones. The Python version of the download machine and the server must match (binary wheels such as <code>charset-normalizer</code>).</p>') + '''
<h2>Install from source (development)</h2>
''' + code('''
pip install -e packages/agent_helper
# or without installing: add packages/agent_helper to sys.path
''', 'bash') + '''
<h2>Add to your project</h2>
''' + code('''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'django_jalali',
    'agent_helper',
    'myplugin',            # your plugin
]
''') + code('''
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path('api/assistant/', include('agent_helper.urls')),
]
''') + code('''
python manage.py migrate agent_helper
''', 'bash') + '''
<h2>Verify the installation</h2>
''' + code('''
python manage.py check            # agent_helper.E001 means a tool points to an unregistered action kind
python manage.py test agent_helper
''', 'bash') + '''
<p>Tables created: conversation, message, pending action, audit, request log, model call log and tool call log (full list in <a href="concepts.html">Concepts</a>).</p>
'''
    return page('installation', 'Installation', 'Offline install from wheels, adding the app to a project, and migrate', body)


def tutorial():
    body = '''
<p>In this tutorial we create an empty project and write a plugin called <code>notes</code> that reads the user's notes and
<b>proposes</b> adding a note (saved only when the user presses the button). Very similar code ships in the <code>agent-helper-demo</code> package.</p>
<h2>1. Project and install</h2>
''' + code('''
python -m venv venv && . venv/bin/activate
pip install --no-index --find-links wheelhouse --find-links dist --pre agent-helper
django-admin startproject mysite . && python manage.py startapp notes
''', 'bash') + '''
<h2>2. Domain model</h2>
''' + code('''
# notes/models.py
from django.conf import settings
from django.db import models

class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
''') + '''
<h2>3. The plugin</h2>
''' + code('''
# notes/plugin.py
from agent_helper import actions
from agent_helper.plugins import ActionKind, Plugin, PromptFragment, ToolSpec


def list_my_notes(user, args, ctx):
    """Read-only; user is always request.user"""
    from notes.models import Note
    notes = Note.objects.filter(user=user).order_by('-id')[:10]
    return {'count': len(notes), 'notes': [{'id': n.id, 'text': n.text} for n in notes]}


def propose_add_note(user, args, ctx):
    """Proposal only; nothing is saved"""
    text = str(args.get('text') or '').strip()
    if not text:
        return {'error': 'The note text is empty.'}
    action = ctx.propose('add_note', {'text': text})
    return {'status': 'ready', 'action_id': action.id,
            'message': 'Draft is ready; the user must press the button. Do not say it was saved.'}


def execute_add_note(user, action, params):
    """Only from the confirm endpoint, inside a transaction and under a lock"""
    from notes.models import Note
    note = Note.objects.create(user=user, text=action.payload['text'])
    actions.audit(user, action, 'created', 'Note saved', node_id=note.id)
    return {'status': 'confirmed', 'message': 'Note saved.',
            'results': [{'note_id': note.id, 'status': 'success'}], 'status_code': 200}


PLUGIN = Plugin(
    name='notes',
    tools=[
        ToolSpec('list_my_notes', "List the user's notes",
                 {'type': 'object', 'properties': {}}, list_my_notes,
                 status='Reading notes...'),
        ToolSpec('propose_add_note', 'Draft a new note (does not save)',
                 {'type': 'object', 'properties': {'text': {'type': 'string'}}, 'required': ['text']},
                 propose_add_note, read_only=False, proposes='add_note'),
    ],
    actions=[ActionKind('add_note', execute=execute_add_note,
                        preview=lambda p: {'kind': 'add_note', 'text': p['text']},
                        propose_schema={'type': 'object', 'required': ['text']})],
    prompt_fragments=[PromptFragment(
        'Notes: use list_my_notes to read and propose_add_note to add; never say it was saved.', order=60)],
)
''') + code('''
# notes/apps.py
from django.apps import AppConfig

class NotesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notes'

    def ready(self):
        import agent_helper
        from notes.plugin import PLUGIN
        agent_helper.register(PLUGIN)
''') + '''
<h2>4. Settings and URLs</h2>
''' + code('''
# mysite/settings.py
INSTALLED_APPS += ['rest_framework', 'django_jalali', 'agent_helper', 'notes']

AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': 'http://127.0.0.1:8000/v1',
    'LLM_API_KEY': 'sk-local',
    'LLM_MODEL': 'qwen3',
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
}
''') + code('''
# mysite/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/assistant/', include('agent_helper.urls')),
]
''') + code('''
python manage.py makemigrations notes && python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
''', 'bash') + '''
<h2>5. First chat</h2>
<p>As a logged-in user (or with a JWT token if your project uses JWT):</p>
''' + code('''
curl -N -X POST http://127.0.0.1:8000/api/assistant/chat/ \\
     -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' \\
     -d '{"message": "Note that I have a meeting tomorrow at 10"}'
''', 'bash') + code('''
data: {"event": "tool_status", "status": "Running tool propose_add_note..."}

data: {"event": "pending_action", "action_id": 7, "kind": "add_note", "text": "Meeting tomorrow at 10", "expires_at": "1405/07/20 14:10"}

data: {"event": "token", "text": "Your note draft is ready; press confirm to save it."}

data: {"event": "done", "conversation_id": 3, "message_id": 12, "path": "llm"}
''', 'text') + '''
<p>The user presses the button and the UI sends the confirmation:</p>
''' + code('''
curl -X POST http://127.0.0.1:8000/api/assistant/actions/7/confirm/ -H 'Authorization: Bearer <token>'
# {"status": "confirmed", "message": "Note saved.", "results": [...]}
''', 'bash') + '''
<h2>6. Tests</h2>
''' + code('''
# notes/tests.py
from django.test import TestCase
from agent_helper.llm import LLMResponse, MockProvider, ToolCall, run_assistant_agent
from agent_helper.models import AssistantConversation
from agent_helper.registry import override
from agent_helper.testing import fast_router, make_user
from notes.plugin import PLUGIN


class NotesTests(TestCase):
    def test_propose_does_not_save(self):
        user = make_user('u1')
        conv = AssistantConversation.objects.create(user=user, title='t')
        provider = MockProvider([
            LLMResponse(tool_calls=[ToolCall(id='1', name='propose_add_note', arguments={'text': 'hello'})]),
            LLMResponse(text='Press the button.'),
        ])
        with override([PLUGIN]), fast_router(on=False):
            events = list(run_assistant_agent(user, conv, 'note: hello', provider=provider))
        self.assertTrue(any(e['event'] == 'pending_action' for e in events))
        self.assertFalse(user.notes.exists())
''') + '''
''' + adm('tip', 'What next?', '<p>The <a href="fast-routes.html">fast path</a> for frequent messages without the LLM, <a href="frontend.html">connecting a frontend</a> and <a href="deployment.html">deployment</a>.</p>')
    return page('tutorial', 'Tutorial: zero to first chat', 'An empty project, a small plugin with one read-only tool and one pending action, and the first SSE request', body)


def concepts():
    body = '''
<h2>Life of a message</h2>
<ol>
<li><b>Entry:</b> <code>POST chat/</code> with an authenticated user; rate limits (per minute / per day); the image attachment is stored if present.</li>
<li><b>Image:</b> if there is an attachment, the vision model extracts its data and the text is appended to the message (the fast path is skipped).</li>
<li><b>Fast path:</b> if enabled: conversation mode, route regexes, one light-model call, then the plugins' routes. It answers only with confidence ≥ threshold.</li>
<li><b>LLM loop:</b> conversation history + relevant tools + a prompt built from fragments; the model calls tools until the final answer (at most 6 rounds).</li>
<li><b>Events:</b> every step is sent as SSE; proposals produce a <code>pending_action</code> card.</li>
<li><b>Execution:</b> only when the user presses the button: <code>POST actions/&lt;id&gt;/confirm/</code>.</li>
<li><b>Logs:</b> one request log row + a log for every model and tool call.</li>
</ol>
<h2>Parts of the plugin contract</h2>
''' + table(['Part', 'Role', 'Page'], [
        ['<code>Plugin</code>', 'Bundles all parts of a plugin; registered with <code>agent_helper.register</code>', '<a href="plugins.html">Writing a plugin</a>'],
        ['<code>ToolSpec</code>', 'A tool the model or the fast path calls; read-only or proposal', '<a href="tools.html">Tools</a>'],
        ['<code>ActionKind</code>', 'A pending action type: card preview and the real execution', '<a href="actions.html">Pending actions</a>'],
        ['<code>FastRoute</code>', 'A no-LLM route (regex, yes/no question, main questions)', '<a href="fast-routes.html">Fast path</a>'],
        ['<code>CatalogProvider</code>', 'Entities the user refers to by name', '<a href="fast-routes.html">Fast path</a>'],
        ['<code>PromptFragment</code>', 'A prompt rule; can replace a core rule', '<a href="prompts.html">Prompt</a>'],
    ]) + '''
<h2>Data models</h2>
''' + table(['Model', 'Purpose'], [
        ['<code>AssistantConversation</code> (alias: <code>Conversation</code>)', 'A conversation per user; <code>mode</code> = multi-step dialog state'],
        ['<code>AssistantMessage</code> (<code>Message</code>)', 'user / assistant messages; JSON content (text and attachment path)'],
        ['<code>PendingAction</code>', 'Pending action: <code>kind</code>, <code>payload</code>, <code>status</code>, <code>expires_at</code>, <code>result</code>'],
        ['<code>ActionAuditLog</code>', 'Audit of each real execution: user, action, item id, status, detail'],
        ['<code>AssistantRequestLog</code> (<code>RequestLog</code>)', 'One row per message: path, reason, intent, call counts, tokens, duration'],
        ['<code>ModelCallLog</code>', 'Each model call (intent / chat / vision)'],
        ['<code>ToolCallLog</code>', 'Each tool run with arguments and a result summary'],
    ]) + '''
<h2>Pending action statuses</h2>
''' + table(['Status', 'Meaning'], [
        ['<code>pending</code>', 'Waiting for the user\'s button (10 minutes by default)'], ['<code>confirmed</code>', 'Executed'],
        ['<code>partial</code>', 'Some items were executed'], ['<code>failed</code>', 'Execution failed (or the executor raised)'],
        ['<code>cancelled</code>', 'The user cancelled, or nothing was selected'], ['<code>expired</code>', 'The deadline passed; it can no longer be confirmed'],
    ]) + '''
<h2>Design principles</h2>
<ul><li><b>The AI proposes, a human executes.</b></li><li><b>Everything is scoped to the current user.</b></li>
<li><b>Cheap and fast first, smart second;</b> a confident wrong answer is worse than a slow one.</li><li><b>Traceable:</b> every decision and call is logged.</li></ul>
'''
    return page('concepts', 'Concepts and architecture', 'The life of a message, the plugin contract, data models and action statuses', body)


def configuration():
    body = '''
<p>All settings live in one <code>AGENT_HELPER</code> dict in <code>settings.py</code>. Each key is resolved in this order:</p>
<ol><li><code>settings.AGENT_HELPER[key]</code></li><li>the matching environment variable (if any)</li><li>the default value</li></ol>
<p>Values are read at the moment of use, so changing an environment variable in tests (<code>mock.patch.dict(os.environ)</code>) takes effect immediately.</p>
<h2>Minimal setup</h2>
''' + code('''
AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': 'http://llm.internal:8000/v1',
    'LLM_MODEL': 'qwen3',
}
''') + '''
<h2>Fast path with Jev</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'USE_FAST_ROUTER': '1',
    'INTENT_BACKEND': 'jev',
    'JEV_BASE_URL': 'http://jev.internal',     # same /v1/systemone contract
    'JEV_API_KEY': '...',
    'FAST_THRESHOLD': 0.8,
}
''') + '''
<h2>Fast path with a local model</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'USE_FAST_ROUTER': '1',
    'INTENT_BACKEND': 'llm',                    # any OpenAI-compatible server that returns logprobs
    'INTENT_BASE_URL': 'http://vllm.internal:8000/v1',
    'INTENT_MODEL': 'qwen3-1.7b',
}
''') + '''
<h2>With environment variables</h2>
''' + code('''
ASSISTANT_LLM_PROVIDER=openai
ASSISTANT_LLM_BASE_URL=http://llm.internal:8000/v1
ASSISTANT_LLM_API_KEY=...
ASSISTANT_LLM_MODEL=qwen3
ASSISTANT_USE_FAST_ROUTER=1
TYPESAFE_BASE_URL=http://jev.internal
TYPESAFE_API_KEY=...
''', 'bash') + '''
<h2>Admin with your project's theme</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'ADMIN_BASE': 'myproject.admin.BaseModelAdmin',       # your project's base admin class
    'ADMIN_INLINE_BASE': 'myproject.admin.BaseTabularInline',
    # 'REGISTER_ADMIN': False,                             # register no admin at all
}
''') + '''
<h2>Assistant identity in the prompt</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'ASSISTANT_TITLE': 'Shop assistant',
    'ASSISTANT_MISSION': "Your job is to answer briefly and precisely about the user's orders.",
}
''') + '''
<p>The full list of keys is in the <a href="settings-ref.html">settings reference</a>.</p>
''' + adm('warn', 'No internet defaults', '<p>If <code>LLM_BASE_URL</code> is not set, no LLM request is made and the user gets a "could not connect to the provider" message. Jev without <code>JEV_BASE_URL</code> fails and the message falls through to the LLM.</p>')
    return page('configuration', 'Configuration', 'AGENT_HELPER settings, environment variables and common examples', body)

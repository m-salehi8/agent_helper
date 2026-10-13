from lib import adm, code, page, sig, table
from pages_ref import conf_defaults


def http_api():
    body = '''
<p>All endpoints are <code>IsAuthenticated</code> and work with your project's DRF authentication classes (JWT, session, token).
Paths are relative to where you included <code>agent_helper.urls</code> (<code>/api/assistant/</code> in the examples).</p>
''' + table(['Method', 'Path', 'URL name', 'Purpose'], [
        ['POST', '<code>chat/</code>', '<code>assistant_chat</code>', 'Send a message; SSE streamed response'],
        ['GET', '<code>conversations/</code>', '<code>assistant_conversations</code>', "The user's conversations"],
        ['GET', '<code>conversations/&lt;id&gt;/</code>', '<code>assistant_conversation_detail</code>', 'One conversation with its messages'],
        ['POST', '<code>actions/&lt;id&gt;/confirm/</code>', '<code>assistant_action_confirm</code>', 'Execute a pending action'],
        ['POST', '<code>actions/&lt;id&gt;/cancel/</code>', '<code>assistant_action_cancel</code>', 'Cancel a pending action'],
    ]) + '''
<h2>POST chat/</h2>
''' + table(['Field', 'Type', 'Description'], [
        ['<code>message</code>', 'string, required, max 5000', 'The user text'],
        ['<code>conversation_id</code>', 'int, optional', "Continue a previous conversation (the user's own only; otherwise 404); empty = new conversation"],
        ['<code>image</code>', 'data URL, optional', 'png/jpg/webp image (<a href="attachments.html">image attachments</a>)'],
    ]) + code('''
POST /api/assistant/chat/
Authorization: Bearer eyJ...
Content-Type: application/json

{"message": "Show my open orders", "conversation_id": 12}
''', 'http') + '''
<p>The response is <code>200 text/event-stream</code>; each event is a <code>data: &lt;JSON&gt;</code> line followed by a blank line. The
<code>Cache-Control: no-cache</code> and <code>X-Accel-Buffering: no</code> headers are set so nginx passes it through unbuffered.</p>
''' + table(['Status', 'When'], [
        ['<code>200</code>', 'Stream (even LLM errors arrive as an <code>error</code> event)'],
        ['<code>400</code>', 'Invalid body (DRF error JSON)'], ['<code>401</code>', 'Not authenticated'],
        ['<code>404</code>', "<code>conversation_id</code> does not belong to the user"],
        ['<code>429</code>', 'Per-minute/daily limit or invalid image; one <code>error</code> event with a user-facing message'],
    ]) + '''
<h2>SSE events</h2>
''' + table(['event', 'Fields', 'Use in the UI'], [
        ['<code>tool_status</code>', '<code>status</code>', 'Status bar ("Working on …")'],
        ['<code>token</code>', '<code>text</code>', 'Answer text (final text only; text before a tool call is not shown)'],
        ['<code>pending_action</code>', '<code>action_id</code>, <code>expires_at</code> + the <code>preview</code> fields', 'Confirm/cancel card'],
        ['<code>attachment_data</code>', '<code>data</code>, <code>warning</code>', '"Read from the image" card'],
        ['<code>done</code>', '<code>conversation_id</code>, <code>message_id</code>, <code>path</code> (<code>fast</code> or <code>llm</code>)', 'End; keep the conversation id'],
        ['<code>error</code>', '<code>message</code> (+ <code>detail</code> in DEBUG)', 'Warning'],
        ['Plugin events', 'Free-form (from <code>ToolSpec.events</code>)', 'Tables, status cards, …'],
    ]) + code('''
data: {"event": "tool_status", "status": "Searching orders..."}

data: {"event": "order_list", "items": [{"id": 5, "total": 120000}], "count": 1}

data: {"event": "token", "text": "You have one open order."}

data: {"event": "done", "conversation_id": 12, "message_id": 88, "path": "fast"}
''', 'text') + '''
<h3>Error messages</h3>
<p>The core's user-facing messages are in Persian; the table gives their meaning.</p>
''' + table(['Case', 'message (meaning)'], [
        ['Model timeout', 'The AI model service timed out…'],
        ['Model 429', 'The AI service is busy right now…'], ['Model 401/403', 'API key validation error…'],
        ['Other HTTP', 'An error occurred while talking to the AI server…'], ['Connection / not configured', 'Could not connect to the provider…'],
    ]) + '''
<h2>POST actions/&lt;id&gt;/confirm/</h2>
<p>Any JSON body, passed unchanged to <code>ActionKind.execute</code> as <code>params</code>.</p>
''' + code('''
POST /api/assistant/actions/45/confirm/
{"node_ids": [1024, 1031], "unchecked": "keep"}

200 {"message": "2 items approved.", "action_id": 45, "status": "confirmed",
     "results": [{"node_id": 1024, "status": "success", "detail": "..."}]}
''', 'http') + table(['Status', 'Body'], [
        ['<code>200</code>', 'Execution result; a repeated confirm: <code>{"already_confirmed": true, "status", "results"}</code>'],
        ['<code>400</code>', '<code>{"error"}</code>: expired, status not pending, unknown kind or invalid parameter'],
        ['<code>403</code>', 'The action belongs to another user'], ['<code>404</code>', 'No such action'],
        ['<code>500</code>', 'The executor raised; the action is <code>failed</code> and audited'],
    ]) + '''
<h2>POST actions/&lt;id&gt;/cancel/</h2>
''' + code('''
200 {"message": "Action cancelled.", "status": "cancelled", "action_id": 45}
''', 'http') + '''
<h2>GET conversations/</h2>
''' + code('''
[{"id": 12, "title": "Show my open orders", "created_at": "1405-07-20 14:02:11", "messages_count": 4}]
''', 'json') + code('''
GET conversations/12/
{"id": 12, "title": "...", "created_at": "...",
 "messages": [{"id": 87, "role": "user", "content": {"text": "..."}, "created_at": "..."},
              {"id": 88, "role": "assistant", "content": {"text": "..."}, "created_at": "..."}]}
''', 'json') + adm('note', 'Pagination', "<p>The conversation list follows your project's <code>DEFAULT_PAGINATION_CLASS</code>.</p>")
    return page('http-api', 'HTTP API and SSE events', 'Endpoints, bodies, status codes and every stream event', body)


def frontend():
    body = '''
<p><code>EventSource</code> only sends GET; for a POST with an auth header use <code>fetch</code> and read the stream.</p>
<h2>Browser client</h2>
''' + code('''
async function chat(message, conversationId, token, onEvent) {
  const res = await fetch('/api/assistant/chat/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
    body: JSON.stringify({message, conversation_id: conversationId}),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});
    const parts = buffer.split('\\n\\n');
    buffer = parts.pop();
    for (const part of parts) {
      if (part.startsWith('data: ')) onEvent(JSON.parse(part.slice(6)));
    }
  }
}

let conversationId = null;
chat('Show my orders', conversationId, TOKEN, ev => {
  if (ev.event === 'token') appendText(ev.text);
  else if (ev.event === 'tool_status') showStatus(ev.status);
  else if (ev.event === 'pending_action') renderActionCard(ev);
  else if (ev.event === 'error') showError(ev.message);
  else if (ev.event === 'done') conversationId = ev.conversation_id;
});
''', 'js') + '''
<h2>Action card</h2>
''' + code('''
function renderActionCard(ev) {
  // show ev.kind and the preview fields
  confirmBtn.onclick = () => act(ev.action_id, 'confirm', {});
  cancelBtn.onclick = () => act(ev.action_id, 'cancel');
}

async function act(id, op, body) {
  const res = await fetch(`/api/assistant/actions/${id}/${op}/`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN},
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  showResult(res.ok ? data.message : data.error);
}
''', 'js') + '''
<h2>Tips</h2>
<ul><li>Keep the conversation id after <code>done</code> so the next message continues the same conversation.</li>
<li>Disable the send button until <code>done</code> or <code>error</code> arrives.</li>
<li>Disable the card after <code>expires_at</code>; the server also rejects expired actions.</li>
<li>Ignore unknown events so a new plugin does not break the client.</li>
<li>Behind nginx: <code>proxy_buffering off</code>, or the <code>X-Accel-Buffering: no</code> header the server already sends.</li></ul>
<h2>Python (script or integration test)</h2>
''' + code('''
import json, requests

with requests.post(url + '/api/assistant/chat/', json={'message': 'hello'},
                   headers={'Authorization': 'Bearer ' + token}, stream=True) as r:
    for block in r.content.decode('utf-8').split('\\n\\n'):
        if block.startswith('data: '):
            print(json.loads(block[6:]))
''')
    return page('frontend', 'Connecting a frontend', 'Reading the SSE stream with fetch, the action card and deployment tips', body)


def python_api():
    rows = [
        ('agent_helper', [
            ('register(plugin)', 'Register a Plugin (in AppConfig.ready)'),
            ('__version__', 'Package version string (PEP 440, e.g. 0.1.0b1)'),
        ]),
        ('agent_helper.plugins', [
            ('Plugin, ToolSpec, ActionKind, FastRoute, PromptFragment', 'The plugin contract (guide pages)'),
            ('CatalogProvider, CatalogEntry(key, title, aliases=(), description=\'\', data=None)', 'Catalogs'),
            ('ToolContext(user, conversation, trace, proposed).propose(kind, payload, minutes=None)', 'Tool context'),
            ('RouteRequest, Defer(reason)', 'Fast-route input and result'),
        ]),
        ('agent_helper.registry', [
            ('registry.tools() / tool(name) / actions() / action(kind) / routes() / catalogs() / fragments() / check()', 'Lookups over registered plugins'),
            ('override(plugins)', 'Context manager: temporarily replace the plugins (tests)'),
        ]),
        ('agent_helper.tools', [
            ('execute_tool(name, arguments, user, conversation=None, ctx=None) -> dict', 'Run one tool for user'),
            ('run_logged(trace, name, args, user, conversation=None, collect=None)', 'Run with logging; proposals go into collect'),
            ('specs(names=None), anthropic_schemas(selected=None), openai_schemas(selected=None), set_mode(conversation, mode)', ''),
        ]),
        ('agent_helper.actions', [
            ('create_pending(user, conversation, kind, payload, minutes=None) -> PendingAction', 'Create a proposal'),
            ('pending_event(action) -> dict', 'The SSE card event'),
            ('confirm_pending_action(user, action_id, params=None) -> dict', 'Same logic as the confirm endpoint (with status_code)'),
            ('cancel_pending_action(user, action_id) -> dict', 'Cancel'),
            ('audit(user, action, status, detail=\'\', **refs)', 'Audit row'),
        ]),
        ('agent_helper.llm', [
            ('run_assistant_agent(user, conversation, user_prompt, provider=None, attachment=None)', 'Event generator; what the view streams'),
            ('get_llm_provider()', 'Provider from settings'),
            ('OpenAICompatibleProvider, AnthropicProvider, MockProvider(responses)', 'Providers'),
            ('LLMResponse(text=None, tool_calls=[], raw={}), ToolCall(id, name, arguments)', 'Model response'),
        ]),
        ('agent_helper.router', [('try_fast_path(user, conversation, text, trace=None)', 'Fast-path reply or None'), ('enabled()', '')]),
        ('agent_helper.nlu', [
            ('classify(text), jev_classify(text, timeout), llm_classify(text, timeout)', 'Light model'),
            ('main_questions(), gate_questions(), jev_questions(), catalog_question(provider)', 'Questions gathered from plugins'),
            ('match_catalog(provider, text, stopwords=()), resolve_catalog(provider, cls, text, stopwords=())', 'Catalog matching'),
            ('JevError', ''),
        ]),
        ('agent_helper.prompts', [('build_system_prompt(tags=None), fragments(), CORE_FRAGMENTS', '')]),
        ('agent_helper.selection', [('select_tags(conversation, text, attachment=None, cls=None), select_tools(tags)', 'Tool selection')]),
        ('agent_helper.fa', [('extract_amount(text), extract_currency(text), normalize(text), to_ascii_digits(s), fa_number(n)', 'Persian text and numbers')]),
        ('agent_helper.vision', [('save_upload(user, data_url) -> path, extract_document(path, trace=None), check_totals(data)', 'Image attachments')]),
        ('agent_helper.conf', [('get(key), flag(key), daily_limit(), DEFAULTS', 'Settings')]),
        ('agent_helper.testing', [('make_user(username), fast_router(on=True, **env)', 'Test helpers')]),
        ('agent_helper.trace', [('RequestTrace(user, conversation, message)', 'Logging of one request: model_call, run_tool, finish')]),
        ('agent_helper.views', [('ChatStreamView, ConversationListView, ConversationDetailView, ActionConfirmView, ActionCancelView, check_rate_limits(user)', 'Views')]),
        ('agent_helper.models', [('AssistantConversation, AssistantMessage, PendingAction, ActionAuditLog, AssistantRequestLog, ModelCallLog, ToolCallLog', 'Aliases: Conversation, Message, RequestLog')]),
    ]
    body = ''
    for mod, items in rows:
        body += f'<h2><code>{mod}</code></h2>' + ''.join(sig(s) + (f'<p>{d}</p>' if d else '') for s, d in items)
    body += adm('note', 'Stability', '<p>The plugin contract (<code>agent_helper.plugins</code>, <code>register</code>, <code>actions.audit</code>, <code>actions.create_pending</code>) is the intended public API. During the beta it may still change; other modules are internal and may change in any release.</p>')
    return page('python-api', 'Python reference', 'Public modules, functions and classes', body)


def settings_ref():
    defaults = conf_defaults()
    desc = {
        'LLM_PROVIDER': '<code>openai</code> (any compatible server) or <code>anthropic</code>', 'LLM_BASE_URL': 'LLM server address (without it the LLM path fails)',
        'LLM_API_KEY': 'Key', 'LLM_MODEL': 'Model name', 'LLM_TIMEOUT': 'Seconds', 'MAX_AGENT_ITERATIONS': 'Max rounds of the tool loop',
        'USE_FAST_ROUTER': 'Enable the fast path (<code>1</code>)', 'FAST_THRESHOLD': 'Minimum fast-path confidence',
        'INTENT_BACKEND': '<code>jev</code> or <code>llm</code>', 'INTENT_TIMEOUT': 'Light-model timeout (seconds)',
        'INTENT_BASE_URL': 'Local intent model server (defaults to the LLM)', 'INTENT_API_KEY': '', 'INTENT_MODEL': '',
        'JEV_BASE_URL': 'Jev server (<code>/v1/systemone</code>)', 'JEV_API_KEY': '', 'JEV_MODEL': '',
        'VISION_BASE_URL': 'Vision model server (defaults to the LLM)', 'VISION_API_KEY': '', 'VISION_MODEL': '', 'VISION_TIMEOUT': 'Seconds',
        'UPLOAD_DIR': 'Image folder in storage', 'MAX_UPLOAD_BYTES': 'Maximum image size',
        'PER_MINUTE_LIMIT': 'Messages per minute per user', 'DAILY_LIMIT': 'Daily limit (None ⇒ <code>settings.ASSISTANT_DAILY_LIMIT</code> or 100)',
        'ACTION_EXPIRES_MINUTES': 'Default pending action lifetime', 'TOOL_SELECTION': '<code>auto</code> or <code>all</code>',
        'REGISTER_ADMIN': 'Register model admins', 'ADMIN_BASE': 'Base ModelAdmin class', 'ADMIN_INLINE_BASE': 'Base inline class',
        'ASSISTANT_TITLE': 'Assistant name in the prompt', 'ASSISTANT_MISSION': 'Mission sentence in the prompt', 'TODAY_LINE': "Today's Jalali date line in the prompt",
    }
    rows = [[f'<code>{k}</code>', f'<code>{env}</code>' if env else '—', f'<code>{default!r}</code>', desc.get(k, '')]
            for k, (env, default) in defaults.items()]
    rows.append(['<code>TEST_USER_FACTORY</code>', '—', '<code>None</code>', 'Dotted path of a <code>(username) -&gt; user</code> function for <code>testing.make_user</code>'])
    body = '''
<p>Everything lives in <code>settings.AGENT_HELPER</code>. Order: settings ⇒ environment variable ⇒ default. Environment values are converted to the default's type (number, boolean).</p>
''' + table(['Key', 'Environment variable', 'Default', 'Description'], rows) + '''
<h2>Related Django settings</h2>
''' + table(['Setting', 'Effect'], [
        ['<code>AUTH_USER_MODEL</code>', "All FKs point to the project's user model"],
        ['<code>REST_FRAMEWORK</code>', 'Authentication and pagination of the endpoints'],
        ['<code>CACHES</code>', 'Rate-limit counters (use Redis/Memcached with several processes)'],
        ['<code>DEFAULT_FILE_STORAGE</code> / <code>STORAGES</code>', 'Where attached images are stored'],
        ['<code>MIGRATION_MODULES</code>', 'Only for installing on existing legacy tables (<a href="deployment.html">deployment</a>)'],
    ])
    return page('settings-ref', 'Settings reference', 'Every AGENT_HELPER key with its environment variable and default', body)

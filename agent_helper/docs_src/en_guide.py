from lib import adm, code, page, sig, table


def plugins():
    body = '''
<p>A plugin is an ordinary Django app that registers a <code>Plugin</code> object in <code>AppConfig.ready()</code>. The core
knows nothing about the domain; all knowledge (tools, actions, prompt rules, fast routes) lives in the plugin.</p>
<h2>Suggested layout</h2>
''' + code('''
myplugin/
├── apps.py          # register(PLUGIN) in ready()
├── models.py        # domain models (if needed)
├── plugin.py        # ToolSpecs, ActionKinds, PromptFragments, FastRoutes and PLUGIN
├── services.py      # domain logic (queries, validation, execution)
└── tests/
''', 'text') + '''
<h2>Plugin</h2>
''' + sig("Plugin(name, tools=(), actions=(), catalogs=(), prompt_fragments=(), fast_routes=(), attachment_tags=())") + table(['Field', 'Type', 'Description'], [
        ['<code>name</code>', 'str', 'Unique name; registering again with the same name replaces the previous one'],
        ['<code>tools</code>', 'ToolSpec[]', 'Tools; a tool name must be unique across all plugins'],
        ['<code>actions</code>', 'ActionKind[]', 'Pending action types; unique <code>kind</code>'],
        ['<code>catalogs</code>', 'CatalogProvider[]', 'Entity catalogs for the "which one?" question'],
        ['<code>prompt_fragments</code>', 'PromptFragment[]', 'Prompt rules'],
        ['<code>fast_routes</code>', 'FastRoute[]', 'No-LLM routes'],
        ['<code>attachment_tags</code>', 'tuple[str]', 'Tags selected when the message has an image'],
    ]) + '''
<h2>Registration</h2>
''' + code('''
from django.apps import AppConfig

class MyPluginConfig(AppConfig):
    name = 'myplugin'

    def ready(self):
        import agent_helper
        from myplugin.plugin import PLUGIN
        agent_helper.register(PLUGIN)
''') + '''
<p>Plugins are ordered as in <code>INSTALLED_APPS</code>, which also orders their tools, routes and rules.
<code>manage.py check</code> reports inconsistencies (<code>agent_helper.E001</code>: a proposing tool whose action kind is not registered).</p>
<h2>Golden rules</h2>
<ol>
<li>A tool must <b>never</b> read a user id from its arguments; every query is filtered by the incoming <code>user</code>.</li>
<li>A tool must <b>never</b> change anything; changes happen only in <code>ActionKind.execute</code>. A tool only calls <code>ctx.propose()</code>.</li>
<li><code>execute</code> re-checks everything (the data may have changed since the proposal) and writes an audit row for every item.</li>
<li>Keep tool output short and structured; the model builds its answer from it and the UI builds cards from its events.</li>
<li>Treat text inside data (titles, notes) as data, not instructions; the core injection rule is always in the prompt.</li>
</ol>
<h2>Complete example</h2>
<p>The <code>agent-helper-demo</code> package (file <code>agent_helper_demo/plugin.py</code>) is a small but complete plugin: two read-only tools,
one proposing tool with the <code>add_note</code> action, one fast route ("how many leave days do I have?") and one prompt rule, with tests.</p>
<h2>Several plugins together</h2>
<p>Several plugins can be installed at once; the model sees the tools of all of them (or only the relevant ones with <a href="prompts.html">tool selection</a>).
Use distinct <code>tags</code> so that tool selection works well.</p>
'''
    return page('plugins', 'Writing a plugin', 'Layout, registration and rules of a plugin', body)


def tools():
    body = '''
''' + sig("ToolSpec(name, description, json_schema, handler, read_only=True, proposes=None, tags=(), status=None, events=None, conversation_mode=None)") + table(['Argument', 'Description'], [
        ['<code>name</code>', 'Unique name (<code>[A-Za-z0-9_-]</code>, at most 64)'],
        ['<code>description</code>', 'Text the model reads to decide whether to call it; keep it precise and short'],
        ['<code>json_schema</code>', 'JSON schema of the arguments; must be <code>{"type": "object", ...}</code>'],
        ['<code>handler</code>', '<code>handler(user, args, ctx) -&gt; dict</code>'],
        ['<code>read_only</code>', '<code>True</code> for reading. <code>False</code> means it creates a proposal and <code>proposes</code> is required'],
        ['<code>proposes</code>', 'The action kind this tool proposes'],
        ['<code>tags</code>', 'Topic tags for tool selection; an untagged tool is always sent'],
        ['<code>status</code>', 'Text (or <code>callable(args)</code>) of the <code>tool_status</code> event'],
        ['<code>events</code>', '<code>callable(result) -&gt; [event, ...]</code> extra SSE events (e.g. a table)'],
        ['<code>conversation_mode</code>', 'If not None, sets <code>conversation.mode</code> before running'],
    ]) + '''
<h2>handler</h2>
''' + sig("handler(user, args: dict, ctx: ToolContext) -> dict") + '''
<ul><li><code>user</code>: the authenticated user of the request; never taken from the arguments.</li>
<li><code>args</code>: the model's arguments (always a dict; may be incomplete or wrong — validate them).</li>
<li><code>ctx.conversation</code>: the current conversation (or None when run directly).</li>
<li><code>ctx.propose(kind, payload, minutes=None)</code>: creates a pending action; the core sends the card itself.</li></ul>
<p>Return errors as <code>{"error": "..."}</code> so the model can explain them to the user; an unhandled exception becomes a generic error.</p>
''' + code('''
def get_order(user, args, ctx):
    try:
        order_id = int(args.get('order_id'))
    except (TypeError, ValueError):
        return {'error': 'order_id must be a number.'}
    order = Order.objects.filter(id=order_id, user=user).first()   # always scoped to user
    if not order:
        return {'error': 'Order not found or not yours.'}
    return {'id': order.id, 'status': order.get_status_display(), 'total': order.total}


GET_ORDER = ToolSpec(
    name='get_order',
    description="Details of one of the user's own orders by id",
    json_schema={'type': 'object', 'properties': {'order_id': {'type': 'integer'}}, 'required': ['order_id']},
    handler=get_order,
    tags=('orders',),
    status=lambda args: f'Fetching order {args.get("order_id")}...',
)
''') + '''
<h2>Custom events</h2>
<p>To make the UI show a table or a card, use <code>events</code>. The event name is free; the client must know it.</p>
''' + code('''
def _orders_event(result):
    if not result.get('orders'):
        return []
    return [{'event': 'order_list', 'items': result['orders'], 'count': len(result['orders'])}]

ToolSpec('list_orders', '...', SCHEMA, list_orders, events=_orders_event)
''') + '''
<h2>Proposing tool</h2>
''' + code('''
def propose_cancel(user, args, ctx):
    order = Order.objects.filter(id=args.get('order_id'), user=user, status='open').first()
    if not order:
        return {'error': 'You have no open order with this number.'}
    action = ctx.propose('cancel_order', {'order_id': order.id, 'total': order.total})
    return {'status': 'ready', 'action_id': action.id,
            'message': 'Cancellation draft is ready; tell the user to press the button. Never say it was cancelled.'}

ToolSpec('propose_cancel', 'Draft the cancellation of an open order (does not cancel)', SCHEMA, propose_cancel,
         read_only=False, proposes='cancel_order', tags=('orders',))
''') + '''
''' + adm('note', 'Multi-step dialogs', '<p>For forms that take several question-and-answer turns, pass <code>conversation_mode=\'create\'</code> (or any other name). Until the mode is cleared, the user\'s short messages ("November 15") do not go to the fast path. Other tools clear the mode with <code>conversation_mode=\'\'</code>, and an action with <code>resets_mode=True</code> clears it after a successful execution.</p>') + '''
<h2>Running a tool directly</h2>
''' + code('''
from agent_helper import tools
result = tools.execute_tool('get_order', {'order_id': 5}, user=request.user)
''')
    return page('tools', 'Tools (ToolSpec)', 'Defining a tool, the handler, events and proposing tools', body)


def actions_page():
    body = '''
<p>Every data change happens only through a pending action: a tool creates a proposal, the UI shows a card, and only when
the user presses the button is the <code>execute</code> of that action kind run.</p>
''' + sig("ActionKind(kind, execute, preview=lambda payload: {}, propose_schema=None, audit_label='', expires_minutes=10, resets_mode=False)") + table(['Argument', 'Description'], [
        ['<code>kind</code>', 'Unique name; stored in <code>PendingAction.kind</code>'],
        ['<code>execute</code>', '<code>execute(user, action, params) -&gt; dict</code>; only from the confirm endpoint'],
        ['<code>preview</code>', '<code>preview(payload) -&gt; dict</code> fields of the <code>pending_action</code> event (what the card shows)'],
        ['<code>propose_schema</code>', 'JSON schema of the proposal; <code>required</code> keys are checked when proposing'],
        ['<code>audit_label</code>', 'Short label in audit rows the core writes (e.g. execution errors)'],
        ['<code>expires_minutes</code>', 'Lifetime of the proposal'],
        ['<code>resets_mode</code>', 'Clear <code>conversation.mode</code> after a successful execution'],
    ]) + '''
<h2>Lifecycle</h2>
<ol><li>The tool calls <code>ctx.propose(kind, payload)</code> ⇒ a <code>PendingAction</code> row with status <code>pending</code>.</li>
<li>The core sends the <code>pending_action</code> event = <code>{event, action_id, ...preview(payload), expires_at}</code>.</li>
<li>The user presses the button ⇒ <code>POST actions/&lt;id&gt;/confirm/</code> (any body, e.g. the ticked rows).</li>
<li>Inside a transaction the core checks: row lock, ownership (403), idempotency (a repeat returns the previous result), status, expiry.</li>
<li><code>execute(user, action, params)</code> runs inside a savepoint.</li>
<li>The core stores the final status, execution time and result.</li></ol>
<h2>execute return contract</h2>
''' + table(['Return value', 'Effect'], [
        ['<code>{"status": "confirmed" | "partial" | "failed" | "cancelled", "message", "results": [...], "status_code": 200}</code>', 'The action is finalised; <code>results</code> is stored in <code>action.result</code>'],
        ['<code>{"error": "...", "status_code": 400}</code> (no <code>status</code>)', 'The request is rejected but the action stays <code>pending</code> (e.g. invalid parameter)'],
        ['Exception', 'The core audits it, marks the action <code>failed</code> and responds 500; no half-done change remains'],
    ]) + code('''
from agent_helper import actions
from agent_helper.plugins import ActionKind


def execute_cancel(user, action, params):
    order = Order.objects.select_for_update().filter(id=action.payload['order_id'], user=user).first()
    if order is None or order.status != 'open':                 # check again
        actions.audit(user, action, 'failed', 'Order is no longer open', node_id=action.payload['order_id'])
        return {'status': 'failed', 'message': 'The order can no longer be cancelled.',
                'results': [{'status': 'failed'}], 'status_code': 200}
    order.status = 'cancelled'
    order.save(update_fields=['status'])
    actions.audit(user, action, 'confirmed', 'Order cancelled', node_id=order.id, amount=order.total)
    return {'status': 'confirmed', 'message': f'Order {order.id} was cancelled.',
            'results': [{'order_id': order.id, 'status': 'success'}], 'status_code': 200}


CANCEL_ORDER = ActionKind(
    kind='cancel_order',
    execute=execute_cancel,
    preview=lambda p: {'kind': 'cancel_order', 'order_id': p['order_id'], 'total': p['total']},
    propose_schema={'type': 'object', 'required': ['order_id']},
    audit_label='Cancel order',
)
''') + '''
<h2>Audit</h2>
''' + sig("actions.audit(user, action, status, detail='', node_id=None, flow_id=None, amount=None)") + '''
<p><code>node_id</code> = item id, <code>flow_id</code> = parent object, <code>amount</code> = amount (all optional). Write one row per item.</p>
<h2>Proposing without a tool</h2>
''' + code('''
from agent_helper import actions
action = actions.create_pending(request.user, conversation, 'cancel_order', {'order_id': 5, 'total': 1000})
event = actions.pending_event(action)      # the same SSE card event
''') + adm('danger', 'Never', '<p>In <code>execute</code>, never trust <code>params</code> to choose the user or the object; accept only a subset of the same <code>payload</code> (such as ticked rows that were part of the proposal).</p>')
    return page('actions', 'Pending actions (ActionKind)', 'The only way to change data: proposal, card, button, execution with lock and audit', body)


def fast_routes():
    body = '''
<p>Frequent, simple messages ("hi", "my orders", "how many leave days do I have?") do not need the LLM. The fast path decides
with regexes and one light-model call and runs the tool directly — only when all signals are confident.</p>
''' + adm('note', 'Turning it on', '<p><code>AGENT_HELPER[\'USE_FAST_ROUTER\'] = \'1\'</code> (or <code>ASSISTANT_USE_FAST_ROUTER=1</code>). Off ⇒ every message goes to the LLM.</p>') + '''
<h2>Decision order</h2>
<ol>
<li>The conversation is in a mode (<code>conversation.mode</code>) ⇒ LLM (reason: <code>&lt;mode&gt;_dialog</code>).</li>
<li>Gate routes in <code>order</code>: if <code>guard(text)</code> is true ⇒ that route, without the light model.</li>
<li>One light-model call with all questions (error or timeout ⇒ LLM with reason <code>classifier_error</code>).</li>
<li>Yes/no gate questions: two confident gates ⇒ LLM (<code>a_or_b_ambiguous</code>); one ⇒ that route (unless <code>gate_veto</code>).</li>
<li>Main routes in order with the light-model answers; none ⇒ LLM (<code>no_route</code>).</li></ol>
<h2>FastRoute</h2>
''' + sig("FastRoute(name, handler=None, guard=None, gate_question=None, gate_veto=None, questions={}, tags=(), intent_tags={}, order=100)") + table(['Argument', 'Description'], [
        ['<code>name</code>', 'Route name; its yes/no question is asked under the key <code>is_&lt;name&gt;</code>'],
        ['<code>handler</code>', '<code>handler(req: RouteRequest) -&gt; reply | Defer | None</code>; a gate without a handler means "always LLM"'],
        ['<code>guard</code>', '<code>callable(text) -&gt; bool</code> cheap regex; on a match the route runs without the light model'],
        ['<code>gate_question</code>', 'Jev yes/no question (<code>{"type": "noul", ...}</code>)'],
        ['<code>gate_veto</code>', '<code>callable(text) -&gt; bool</code>; ignores a Jev "yes" for this text'],
        ['<code>questions</code>', 'Choice questions of a main route (asked by both backends)'],
        ['<code>tags</code>', 'Related tool/prompt tags (for tool selection on the LLM path)'],
        ['<code>intent_tags</code>', 'Maps answers of the <code>intent</code> question to tags'],
        ['<code>order</code>', 'Execution order (smaller first)'],
    ]) + '''
<h2>RouteRequest</h2>
''' + table(['Member', 'Description'], [
        ['<code>user</code>, <code>conversation</code>, <code>text</code>', 'Inputs'],
        ['<code>cls</code>', 'Light-model answers: <code>{key: {"choice", "confidence", "p"?}}</code>; None when it came from a guard'],
        ['<code>threshold</code>', 'Confidence threshold (<code>FAST_THRESHOLD</code>)'],
        ['<code>gate_p</code>', 'Probability of "yes" per gate: <code>{route_name: p}</code>'],
        ['<code>run_tool(name, args)</code>', 'Runs a registered tool for this same user, with logging'],
        ['<code>reply(text, events=None)</code>', 'Final reply; cards for created proposals are added automatically'],
    ]) + '''
<p>Return <code>Defer('reason')</code> to hand over to the LLM; the reason is kept in the log (<code>fast_reason</code>).</p>
<h2>Example: a gate route with a regex</h2>
''' + code('''
import re
from agent_helper.plugins import FastRoute

LEAVE = re.compile(r'\\bleave\\b', re.I)
ASK = re.compile(r'how many|how much|left|remaining', re.I)

def leave_route(req):
    result = req.run_tool('get_leave_balance', {})
    return req.reply(f'You have {result["remaining_days"]} leave days left.')

ROUTE = FastRoute(name='leave', handler=leave_route, tags=('leave',),
                  guard=lambda t: bool(LEAVE.search(t) and ASK.search(t)))
''') + '''
<h2>Example: a main route with an intent question</h2>
''' + code('''
from agent_helper.plugins import Defer, FastRoute

QUESTIONS = {
    'intent': {
        'type': 'choice',
        'instructions': 'The user writes to a shop assistant. What does the user want?',
        'criteria': {
            'list': 'List or filter their orders',
            'smalltalk': 'Greeting, thanks or help',
            'other': 'Anything else',
        },
    },
}

def orders_route(req):
    intent = req.cls['intent']
    if intent['confidence'] < req.threshold:
        return Defer('low_intent_confidence')
    if intent['choice'] == 'smalltalk':
        return req.reply('Hi! I can show you your orders.')
    if intent['choice'] == 'list':
        result = req.run_tool('list_orders', {})
        return req.reply(f'You have {result["count"]} orders.',
                         [{'event': 'order_list', 'items': result['orders']}])
    return Defer(f'intent_{intent["choice"]}')

ROUTE = FastRoute(name='orders', handler=orders_route, questions=QUESTIONS,
                  intent_tags={'list': ('orders',)})
''') + '''
<h2>Example: a gate that always sends to the LLM</h2>
''' + code('''
CREATE = FastRoute(
    name='create',                                # log reason: create_request
    guard=lambda t: 'submit' in t.lower(),
    gate_question={'type': 'noul', 'instructions': 'The user wants to submit a NEW request.',
                   'criteria': {'true': 'Asks to create or register something new', 'false': 'Anything else'}},
    tags=('create',),
    order=10,
)
''') + '''
<h2>CatalogProvider</h2>
<p>If users refer to entities by name ("my last order", "the Samsung phone"), build a catalog so the core can give the light model
a "which one?" question, with text matching as a fallback.</p>
''' + code('''
from agent_helper import nlu
from agent_helper.plugins import CatalogEntry, CatalogProvider


class ProductCatalog(CatalogProvider):
    name = 'products'
    question_key = 'product'                         # answer key in req.cls
    instructions = 'Which product does the message refer to?'
    none_label = 'No specific product is mentioned'

    def entries(self):
        return [CatalogEntry(key=str(p.id), title=p.title, aliases=tuple(p.aliases), description=p.summary, data=p)
                for p in Product.objects.filter(active=True)]


def my_route(req):
    entry = nlu.resolve_catalog(ProductCatalog(), req.cls, req.text)   # confident light-model answer, else text match
    ...
''') + '''
<h2>Light-model backend</h2>
''' + table(['Backend', 'Questions', 'Settings'], [
        ['<code>jev</code> (default)', 'Main questions + gate yes/no + catalogs, in one <code>/v1/systemone</code> request', '<code>JEV_BASE_URL</code>, <code>JEV_API_KEY</code>, <code>JEV_MODEL</code>'],
        ['<code>llm</code>', 'Main questions only; each question is a single-letter choice with confidence from logprobs', '<code>INTENT_BASE_URL</code>, <code>INTENT_MODEL</code>'],
    ]) + adm('warn', 'Amounts and numbers in code', '<p>The light model is not a calculator. Extract amounts, dates and ids with code (<code>agent_helper.fa.extract_amount</code> for Persian amounts). Send any constraint the fast path does not understand ("all except the first", a person\'s name) to the LLM so it is not silently ignored.</p>')
    return page('fast-routes', 'Fast path and Jev', 'Answers without the LLM for frequent messages; gates, main routes and catalogs', body)


def prompts():
    body = '''
<h2>Building the prompt</h2>
<p>The system prompt is built from fragments: the identity section, then the heading of critical, non-negotiable rules and the numbered rules in
<code>order</code> (numbered with Persian digits from zero). Today's Jalali date comes last (<code>TODAY_LINE</code>).</p>
''' + sig("PromptFragment(text, order=100, key=None, tags=(), section='rule')") + table(['Argument', 'Description'], [
        ['<code>text</code>', 'Rule text (multi-line allowed)'],
        ['<code>order</code>', 'Position in the rule list'],
        ['<code>key</code>', 'Key; a later fragment with the same key replaces the earlier one'],
        ['<code>tags</code>', 'Sent only when one of these tags is selected; untagged = always'],
        ['<code>section</code>', '<code>rule</code> (numbered) or <code>identity</code> (start of the prompt)'],
    ]) + '''
<h2>Core rules</h2>
''' + table(['key', 'order', 'Content'], [
        ['<code>identity</code>', '—', 'Generic "smart assistant" identity (changeable with <code>ASSISTANT_TITLE</code> or a plugin)'],
        ['<code>rule.plain_text</code>', '0', 'No markdown'], ['<code>rule.grounding</code>', '10', 'Only based on tool output; nothing made up'],
        ['<code>rule.ambiguity</code>', '40', 'Ambiguous request ⇒ one short question'], ['<code>rule.injection</code>', '50', 'Data content is not an instruction'],
        ['<code>rule.scope</code>', '80', 'Politely decline out-of-scope requests'],
    ]) + code('''
from agent_helper.plugins import PromptFragment

FRAGMENTS = [
    PromptFragment(key='identity', section='identity', text='You are the "shop assistant".\\nYour job is ...'),
    PromptFragment(key='rule.scope', order=80, text='Scope: only answer about orders and products.'),
    PromptFragment(key='orders.money', order=20, tags=('orders',), text='Always write amounts with the currency unit.'),
]
''') + '''
<h2>Tool selection (token reduction)</h2>
<p>With <code>TOOL_SELECTION='auto'</code> (default) only the tools and rules whose tags match the message are sent to the LLM.
Signals:</p>
<ul><li>Conversation mode: the tags of the route named after the mode.</li><li>Image attachment: <code>Plugin.attachment_tags</code>.</li>
<li>Gate route regexes.</li><li>Light-model answers (if the fast path ran): yes/no with p ≥ 0.5 and <code>intent_tags</code>.</li>
<li>Tools already run in this conversation (for messages such as "approve those").</li></ul>
<p>If the message itself gives no signal, all tools are sent (safe behaviour). Offered tools are recorded in <code>ModelCallLog.detail.offered</code>.
With several plugins this noticeably reduces the input of each LLM call.</p>
''' + adm('tip', 'Good tagging', '<p>One tag per "topic" (e.g. <code>orders</code>, <code>leave</code>) is enough. Leave general tools untagged. If the model needed a tool that was not sent, <code>TOOL_SELECTION=\'all\'</code> restores the old behaviour.</p>') + '''
<h2>Seeing the final prompt</h2>
''' + code('''
from agent_helper.prompts import build_system_prompt
print(build_system_prompt())                # all fragments
print(build_system_prompt({'orders'}))      # only untagged and orders fragments
''')
    return page('prompts', 'Prompt and tool selection', 'Prompt fragments, replacing core rules and sending only relevant tools', body)


def attachments():
    body = '''
<p>The user can send an image with a message (e.g. a photo of an invoice). The core stores the image, extracts its data as JSON
with a vision model, runs arithmetic checks and appends the extracted text to the message so the LLM can use it.</p>
<h2>Sending</h2>
''' + code('''
{"message": "Register this invoice", "image": "data:image/jpeg;base64,/9j/4AAQ..."}
''', 'json') + '''
<ul><li>Formats: png, jpg, webp; at most <code>MAX_UPLOAD_BYTES</code> (5 MB by default).</li>
<li>Storage path: <code>&lt;UPLOAD_DIR&gt;/&lt;user_id&gt;/&lt;uuid&gt;.&lt;ext&gt;</code> in <code>default_storage</code>.</li>
<li>With an attachment the fast path is skipped and the plugins' <code>attachment_tags</code> are selected.</li></ul>
<h2>Events</h2>
''' + code('''
data: {"event": "tool_status", "status": "Reading the attached image..."}
data: {"event": "attachment_data", "data": {"seller": "...", "total": 23370000, "items": [...]}, "warning": ""}
''', 'text') + '''
<p>If reading fails, an <code>error</code> event is sent; the message is stored but the LLM is not run.</p>
<h2>Vision model configuration</h2>
''' + code('''
AGENT_HELPER = {
    # default: the same LLM_* settings
    'VISION_BASE_URL': 'http://vision.internal:8000/v1',
    'VISION_MODEL': 'qwen2.5-vl',
    'VISION_TIMEOUT': 90,
}
''') + '''
<h2>Using it in a plugin</h2>
<p>The file path is stored in the user message content (<code>message.content["attachment"]</code>); a plugin can link it to domain data
(for example save it in a form's file field). Write a prompt rule tagged for attachments telling the model to treat image values as the form source and to ask about unclear values.</p>
''' + adm('warn', 'Machine-read values', '<p>Image extraction can be wrong; always show the values in the preview card and leave execution to the button.</p>')
    return page('attachments', 'Image attachments', 'Sending an image, extraction with a vision model and use in a plugin', body)

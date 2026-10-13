from lib import adm, code, page, sig, table


def plugins():
    body = '''
<p>افزونه یک اپ معمولی Django است که در <code>AppConfig.ready()</code> یک شیء <code>Plugin</code> را ثبت می‌کند. هسته
هیچ‌چیزی درباره‌ی دامنه نمی‌داند؛ همه‌ی دانش (ابزار، اقدام، قواعد پرامپت، مسیر سریع) در افزونه است.</p>
<h2>ساختار پیشنهادی</h2>
''' + code('''
myplugin/
├── apps.py          # register(PLUGIN) در ready()
├── models.py        # مدل‌های دامنه (اگر لازم است)
├── plugin.py        # ToolSpec ها، ActionKind ها، PromptFragment ها، FastRoute ها و PLUGIN
├── services.py      # منطق دامنه (کوئری‌ها، اعتبارسنجی، اجرا)
└── tests/
''', 'text') + '''
<h2>Plugin</h2>
''' + sig("Plugin(name, tools=(), actions=(), catalogs=(), prompt_fragments=(), fast_routes=(), attachment_tags=())") + table(['فیلد', 'نوع', 'توضیح'], [
        ['<code>name</code>', 'str', 'نام یکتا؛ ثبت دوباره با همین نام جایگزین قبلی می‌شود'],
        ['<code>tools</code>', 'ToolSpec[]', 'ابزارها؛ نام ابزار باید در همه‌ی افزونه‌ها یکتا باشد'],
        ['<code>actions</code>', 'ActionKind[]', 'نوع‌های اقدام معلق؛ <code>kind</code> یکتا'],
        ['<code>catalogs</code>', 'CatalogProvider[]', 'کاتالوگ موجودیت‌ها برای سؤال «کدام؟»'],
        ['<code>prompt_fragments</code>', 'PromptFragment[]', 'قواعد پرامپت'],
        ['<code>fast_routes</code>', 'FastRoute[]', 'مسیرهای بدون LLM'],
        ['<code>attachment_tags</code>', 'tuple[str]', 'برچسب‌هایی که وقتی پیام تصویر دارد انتخاب می‌شوند'],
    ]) + '''
<h2>ثبت</h2>
''' + code('''
from django.apps import AppConfig

class MyPluginConfig(AppConfig):
    name = 'myplugin'

    def ready(self):
        import agent_helper
        from myplugin.plugin import PLUGIN
        agent_helper.register(PLUGIN)
''') + '''
<p>ترتیب افزونه‌ها همان ترتیب <code>INSTALLED_APPS</code> است و ترتیب ابزارها، مسیرها و قواعد هم‌ترتیب را تعیین می‌کند.
<code>manage.py check</code> ناسازگاری‌ها را گزارش می‌کند (<code>agent_helper.E001</code>: ابزار پیشنهاددهنده‌ای که نوع اقدامش ثبت نشده).</p>
<h2>قواعد طلایی</h2>
<ol>
<li>ابزار <b>هرگز</b> شناسه‌ی کاربر را از آرگومان نخواند؛ هر کوئری با <code>user</code> ورودی فیلتر شود.</li>
<li>ابزار <b>هرگز</b> چیزی را تغییر ندهد؛ تغییر فقط در <code>ActionKind.execute</code>. ابزار فقط <code>ctx.propose()</code> می‌کند.</li>
<li><code>execute</code> همه‌چیز را دوباره بررسی کند (ممکن است داده بعد از پیشنهاد عوض شده باشد) و برای هر مورد ممیزی بنویسد.</li>
<li>خروجی ابزار کوتاه و ساختاریافته باشد؛ مدل از روی آن پاسخ می‌سازد و رابط کاربری از رویدادهایش کارت.</li>
<li>متن‌های داخل داده (عنوان، یادداشت) را «داده» بدانید نه دستور؛ قاعده‌ی تزریق هسته همیشه در پرامپت هست.</li>
</ol>
<h2>نمونه‌ی کامل</h2>
<p>پکیج <code>agent-helper-demo</code> (فایل <code>agent_helper_demo/plugin.py</code>) یک افزونه‌ی کامل و کوچک است: دو ابزار فقط‌خواندنی،
یک ابزار پیشنهاد با اقدام <code>add_note</code>، یک مسیر سریع («چند روز مرخصی دارم؟») و یک قاعده‌ی پرامپت، همراه با تست‌ها.</p>
<h2>چند افزونه کنار هم</h2>
<p>چند افزونه می‌توانند هم‌زمان نصب باشند؛ مدل ابزارهای همه را می‌بیند (یا با <a href="prompts.html">انتخاب ابزار</a> فقط مرتبط‌ها را).
از برچسب‌های مجزا (<code>tags</code>) استفاده کنید تا انتخاب ابزار درست کار کند.</p>
'''
    return page('plugins', 'نوشتن افزونه', 'ساختار، ثبت و قواعد یک افزونه', body)


def tools():
    body = '''
''' + sig("ToolSpec(name, description, json_schema, handler, read_only=True, proposes=None, tags=(), status=None, events=None, conversation_mode=None)") + table(['آرگومان', 'توضیح'], [
        ['<code>name</code>', 'نام یکتا (<code>[A-Za-z0-9_-]</code>، حداکثر ۶۴)'],
        ['<code>description</code>', 'متنی که مدل برای تصمیم به صدا زدن می‌خواند؛ دقیق و کوتاه بنویسید'],
        ['<code>json_schema</code>', 'JSON schema آرگومان‌ها؛ باید <code>{"type": "object", ...}</code> باشد'],
        ['<code>handler</code>', '<code>handler(user, args, ctx) -&gt; dict</code>'],
        ['<code>read_only</code>', '<code>True</code> برای خواندن. <code>False</code> یعنی پیشنهاد می‌سازد و حتماً <code>proposes</code> لازم است'],
        ['<code>proposes</code>', 'نوع اقدامی که این ابزار پیشنهاد می‌دهد'],
        ['<code>tags</code>', 'برچسب‌های موضوعی برای انتخاب ابزار؛ ابزار بی‌برچسب همیشه فرستاده می‌شود'],
        ['<code>status</code>', 'متن (یا <code>callable(args)</code>) رویداد <code>tool_status</code>'],
        ['<code>events</code>', '<code>callable(result) -&gt; [event, ...]</code> رویدادهای SSE اضافه (مثلاً جدول)'],
        ['<code>conversation_mode</code>', 'اگر None نباشد قبل از اجرا <code>conversation.mode</code> را تنظیم می‌کند'],
    ]) + '''
<h2>handler</h2>
''' + sig("handler(user, args: dict, ctx: ToolContext) -> dict") + '''
<ul><li><code>user</code>: کاربر احرازشده‌ی درخواست؛ هرگز از آرگومان‌ها نیست.</li>
<li><code>args</code>: آرگومان‌های مدل (همیشه dict؛ ممکن است ناقص یا اشتباه باشد — اعتبارسنجی کنید).</li>
<li><code>ctx.conversation</code>: گفتگوی جاری (یا None در اجرای مستقیم).</li>
<li><code>ctx.propose(kind, payload, minutes=None)</code>: ساخت اقدام معلق؛ هسته کارت را خودش می‌فرستد.</li></ul>
<p>خطا را با <code>{"error": "..."}</code> برگردانید تا مدل به کاربر توضیح دهد؛ استثنای بدون مدیریت به خطای عمومی تبدیل می‌شود.</p>
''' + code('''
def get_order(user, args, ctx):
    try:
        order_id = int(args.get('order_id'))
    except (TypeError, ValueError):
        return {'error': 'order_id باید عدد باشد.'}
    order = Order.objects.filter(id=order_id, user=user).first()   # همیشه محدود به user
    if not order:
        return {'error': 'سفارش پیدا نشد یا متعلق به شما نیست.'}
    return {'id': order.id, 'status': order.get_status_display(), 'total': order.total}


GET_ORDER = ToolSpec(
    name='get_order',
    description='جزئیات یک سفارش خود کاربر با شناسه',
    json_schema={'type': 'object', 'properties': {'order_id': {'type': 'integer'}}, 'required': ['order_id']},
    handler=get_order,
    tags=('orders',),
    status=lambda args: f'در حال دریافت سفارش {args.get("order_id")}...',
)
''') + '''
<h2>رویدادهای اختصاصی</h2>
<p>برای اینکه رابط کاربری جدول یا کارت نشان دهد، از <code>events</code> استفاده کنید. نام رویداد آزاد است؛ کلاینت باید آن را بشناسد.</p>
''' + code('''
def _orders_event(result):
    if not result.get('orders'):
        return []
    return [{'event': 'order_list', 'items': result['orders'], 'count': len(result['orders'])}]

ToolSpec('list_orders', '...', SCHEMA, list_orders, events=_orders_event)
''') + '''
<h2>ابزار پیشنهاددهنده</h2>
''' + code('''
def propose_cancel(user, args, ctx):
    order = Order.objects.filter(id=args.get('order_id'), user=user, status='open').first()
    if not order:
        return {'error': 'سفارش باز با این شماره ندارید.'}
    action = ctx.propose('cancel_order', {'order_id': order.id, 'total': order.total})
    return {'status': 'ready', 'action_id': action.id,
            'message': 'پیش‌نویس لغو آماده است؛ به کاربر بگو دکمه را بزند. هرگز نگو لغو شد.'}

ToolSpec('propose_cancel', 'پیش‌نویس لغو یک سفارش باز (لغو نمی‌کند)', SCHEMA, propose_cancel,
         read_only=False, proposes='cancel_order', tags=('orders',))
''') + '''
''' + adm('note', 'گفتگوی چندمرحله‌ای', '<p>برای فرم‌هایی که چند نوبت پرسش و پاسخ دارند، <code>conversation_mode=\'create\'</code> (یا هر نام دیگر) بدهید. تا وقتی حالت خالی نشده، پیام‌های کوتاه کاربر («۲۵ آبان») به مسیر سریع نمی‌روند. ابزارهای دیگر با <code>conversation_mode=\'\'</code> حالت را پاک می‌کنند و اقدام با <code>resets_mode=True</code> بعد از اجرای موفق.</p>') + '''
<h2>اجرای مستقیم</h2>
''' + code('''
from agent_helper import tools
result = tools.execute_tool('get_order', {'order_id': 5}, user=request.user)
''')
    return page('tools', 'ابزارها (ToolSpec)', 'تعریف ابزار، handler، رویدادها و ابزار پیشنهاددهنده', body)


def actions_page():
    body = '''
<p>هر تغییری در داده فقط از راه اقدام معلق انجام می‌شود: ابزار پیشنهاد می‌سازد، رابط کاربری کارت نشان می‌دهد و فقط وقتی
کاربر دکمه را بزند، <code>execute</code> همان نوع اقدام اجرا می‌شود.</p>
''' + sig("ActionKind(kind, execute, preview=lambda payload: {}, propose_schema=None, audit_label='', expires_minutes=10, resets_mode=False)") + table(['آرگومان', 'توضیح'], [
        ['<code>kind</code>', 'نام یکتا؛ در <code>PendingAction.kind</code> ذخیره می‌شود'],
        ['<code>execute</code>', '<code>execute(user, action, params) -&gt; dict</code>؛ فقط از endpoint تایید'],
        ['<code>preview</code>', '<code>preview(payload) -&gt; dict</code> فیلدهای رویداد <code>pending_action</code> (آنچه کارت نشان می‌دهد)'],
        ['<code>propose_schema</code>', 'JSON schema پیشنهاد؛ کلیدهای <code>required</code> هنگام پیشنهاد بررسی می‌شوند'],
        ['<code>audit_label</code>', 'برچسب کوتاه در ممیزی‌هایی که هسته می‌نویسد (مثلاً خطای اجرا)'],
        ['<code>expires_minutes</code>', 'عمر پیشنهاد'],
        ['<code>resets_mode</code>', 'بعد از اجرای موفق <code>conversation.mode</code> پاک شود'],
    ]) + '''
<h2>چرخه‌ی عمر</h2>
<ol><li>ابزار <code>ctx.propose(kind, payload)</code> ⇐ ردیف <code>PendingAction</code> با وضعیت <code>pending</code>.</li>
<li>هسته رویداد <code>pending_action</code> = <code>{event, action_id, ...preview(payload), expires_at}</code> می‌فرستد.</li>
<li>کاربر دکمه را می‌زند ⇐ <code>POST actions/&lt;id&gt;/confirm/</code> (بدنه‌ی دلخواه، مثلاً ردیف‌های تیک‌خورده).</li>
<li>هسته داخل تراکنش: قفل ردیف، مالکیت (۴۰۳)، idempotent (اجرای دوباره نتیجه‌ی قبلی را برمی‌گرداند)، وضعیت، مهلت.</li>
<li><code>execute(user, action, params)</code> داخل یک savepoint اجرا می‌شود.</li>
<li>هسته وضعیت نهایی، زمان اجرا و نتیجه را ذخیره می‌کند.</li></ol>
<h2>قرارداد خروجی execute</h2>
''' + table(['خروجی', 'اثر'], [
        ['<code>{"status": "confirmed" | "partial" | "failed" | "cancelled", "message", "results": [...], "status_code": 200}</code>', 'اقدام نهایی می‌شود؛ <code>results</code> در <code>action.result</code> ذخیره می‌شود'],
        ['<code>{"error": "...", "status_code": 400}</code> (بدون <code>status</code>)', 'درخواست رد می‌شود ولی اقدام <code>pending</code> می‌ماند (مثلاً پارامتر نامعتبر)'],
        ['استثنا', 'هسته آن را ممیزی می‌کند، اقدام <code>failed</code> و پاسخ ۵۰۰؛ هیچ تغییر نیمه‌کاره‌ای نمی‌ماند'],
    ]) + code('''
from agent_helper import actions
from agent_helper.plugins import ActionKind


def execute_cancel(user, action, params):
    order = Order.objects.select_for_update().filter(id=action.payload['order_id'], user=user).first()
    if order is None or order.status != 'open':                 # دوباره بررسی کن
        actions.audit(user, action, 'failed', 'سفارش دیگر باز نیست', node_id=action.payload['order_id'])
        return {'status': 'failed', 'message': 'سفارش دیگر قابل لغو نیست.',
                'results': [{'status': 'failed'}], 'status_code': 200}
    order.status = 'cancelled'
    order.save(update_fields=['status'])
    actions.audit(user, action, 'confirmed', 'لغو سفارش', node_id=order.id, amount=order.total)
    return {'status': 'confirmed', 'message': f'سفارش {order.id} لغو شد.',
            'results': [{'order_id': order.id, 'status': 'success'}], 'status_code': 200}


CANCEL_ORDER = ActionKind(
    kind='cancel_order',
    execute=execute_cancel,
    preview=lambda p: {'kind': 'cancel_order', 'order_id': p['order_id'], 'total': p['total']},
    propose_schema={'type': 'object', 'required': ['order_id']},
    audit_label='لغو سفارش',
)
''') + '''
<h2>ممیزی</h2>
''' + sig("actions.audit(user, action, status, detail='', node_id=None, flow_id=None, amount=None)") + '''
<p><code>node_id</code> = شناسه‌ی مورد، <code>flow_id</code> = شیء والد، <code>amount</code> = مبلغ (همه اختیاری). برای هر مورد یک ردیف بنویسید.</p>
<h2>پیشنهاد بدون ابزار</h2>
''' + code('''
from agent_helper import actions
action = actions.create_pending(request.user, conversation, 'cancel_order', {'order_id': 5, 'total': 1000})
event = actions.pending_event(action)      # همان رویداد SSE کارت
''') + adm('danger', 'هرگز', '<p>در <code>execute</code> به <code>params</code> برای انتخاب کاربر یا شیء اعتماد نکنید؛ فقط زیرمجموعه‌ای از همان <code>payload</code> را بپذیرید (مثل ردیف‌های تیک‌خورده‌ای که در خود پیشنهاد بودند).</p>')
    return page('actions', 'اقدام معلق (ActionKind)', 'تنها راه تغییر داده: پیشنهاد، کارت، دکمه، اجرا با قفل و ممیزی', body)


def fast_routes():
    body = '''
<p>پیام‌های پرتکرار و ساده («سلام»، «سفارش‌هایم»، «چند روز مرخصی دارم؟») لازم نیست به LLM بروند. مسیر سریع با
regex و یک فراخوانی مدل سبک تصمیم می‌گیرد و ابزار را مستقیم اجرا می‌کند. فقط وقتی همه‌ی سیگنال‌ها مطمئن‌اند.</p>
''' + adm('note', 'روشن کردن', '<p><code>AGENT_HELPER[\'USE_FAST_ROUTER\'] = \'1\'</code> (یا <code>ASSISTANT_USE_FAST_ROUTER=1</code>). خاموش ⇐ همه‌ی پیام‌ها به LLM.</p>') + '''
<h2>ترتیب تصمیم</h2>
<ol>
<li>گفتگو در حالتی است (<code>conversation.mode</code>) ⇐ LLM (دلیل: <code>&lt;mode&gt;_dialog</code>).</li>
<li>مسیرهای دروازه به ترتیب <code>order</code>: اگر <code>guard(text)</code> درست بود ⇐ همان مسیر، بدون مدل سبک.</li>
<li>یک فراخوانی مدل سبک با همه‌ی سؤال‌ها (خطا یا timeout ⇐ LLM با دلیل <code>classifier_error</code>).</li>
<li>سؤال‌های بله/خیر دروازه‌ها: دو دروازه مطمئن ⇐ LLM (<code>a_or_b_ambiguous</code>)؛ یکی ⇐ همان مسیر (مگر <code>gate_veto</code>).</li>
<li>مسیرهای اصلی به ترتیب با پاسخ‌های مدل سبک؛ هیچ‌کدام ⇐ LLM (<code>no_route</code>).</li></ol>
<h2>FastRoute</h2>
''' + sig("FastRoute(name, handler=None, guard=None, gate_question=None, gate_veto=None, questions={}, tags=(), intent_tags={}, order=100)") + table(['آرگومان', 'توضیح'], [
        ['<code>name</code>', 'نام مسیر؛ سؤال بله/خیرش با کلید <code>is_&lt;name&gt;</code> پرسیده می‌شود'],
        ['<code>handler</code>', '<code>handler(req: RouteRequest) -&gt; reply | Defer | None</code>؛ دروازه‌ی بدون handler یعنی «همیشه LLM»'],
        ['<code>guard</code>', '<code>callable(text) -&gt; bool</code> regex ارزان؛ اگر جور شد مسیر بدون مدل سبک اجرا می‌شود'],
        ['<code>gate_question</code>', 'سؤال بله/خیر Jev (<code>{"type": "noul", ...}</code>)'],
        ['<code>gate_veto</code>', '<code>callable(text) -&gt; bool</code>؛ پاسخ «بله»ی Jev را برای این متن نادیده می‌گیرد'],
        ['<code>questions</code>', 'سؤال‌های انتخابی مسیر اصلی (در هر دو backend پرسیده می‌شوند)'],
        ['<code>tags</code>', 'برچسب‌های ابزار/پرامپت مرتبط (برای انتخاب ابزار در مسیر LLM)'],
        ['<code>intent_tags</code>', 'نگاشت پاسخ سؤال <code>intent</code> به برچسب‌ها'],
        ['<code>order</code>', 'ترتیب اجرا (کوچک‌تر اول)'],
    ]) + '''
<h2>RouteRequest</h2>
''' + table(['عضو', 'توضیح'], [
        ['<code>user</code>، <code>conversation</code>، <code>text</code>', 'ورودی‌ها'],
        ['<code>cls</code>', 'پاسخ‌های مدل سبک: <code>{key: {"choice", "confidence", "p"?}}</code>؛ None اگر از guard آمده'],
        ['<code>threshold</code>', 'آستانه‌ی اطمینان (<code>FAST_THRESHOLD</code>)'],
        ['<code>gate_p</code>', 'احتمال «بله» هر دروازه: <code>{route_name: p}</code>'],
        ['<code>run_tool(name, args)</code>', 'اجرای ابزار ثبت‌شده برای همین کاربر، با لاگ'],
        ['<code>reply(text, events=None)</code>', 'پاسخ نهایی؛ کارت پیشنهادهای ساخته‌شده خودکار اضافه می‌شود'],
    ]) + '''
<p>برای رفتن به LLM <code>Defer('reason')</code> برگردانید؛ دلیل در لاگ (<code>fast_reason</code>) می‌ماند.</p>
<h2>نمونه: مسیر دروازه با regex</h2>
''' + code('''
import re
from agent_helper.plugins import FastRoute

LEAVE = re.compile(r'مرخصی')
ASK = re.compile(r'چند|چقدر|مانده|باقی')

def leave_route(req):
    result = req.run_tool('get_leave_balance', {})
    return req.reply(f'{result["remaining_days"]} روز مرخصی برایتان مانده است.')

ROUTE = FastRoute(name='leave', handler=leave_route, tags=('leave',),
                  guard=lambda t: bool(LEAVE.search(t) and ASK.search(t)))
''') + '''
<h2>نمونه: مسیر اصلی با سؤال نیت</h2>
''' + code('''
from agent_helper.plugins import Defer, FastRoute

QUESTIONS = {
    'intent': {
        'type': 'choice',
        'instructions': 'The user writes in Persian to a shop assistant. What does the user want?',
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
        return req.reply('سلام! می‌توانم سفارش‌هایتان را نشان بدهم.')
    if intent['choice'] == 'list':
        result = req.run_tool('list_orders', {})
        return req.reply(f'{result["count"]} سفارش دارید.',
                         [{'event': 'order_list', 'items': result['orders']}])
    return Defer(f'intent_{intent["choice"]}')

ROUTE = FastRoute(name='orders', handler=orders_route, questions=QUESTIONS,
                  intent_tags={'list': ('orders',)})
''') + '''
<h2>نمونه: دروازه‌ای که همیشه به LLM می‌فرستد</h2>
''' + code('''
CREATE = FastRoute(
    name='create',                                # دلیل لاگ: create_request
    guard=lambda t: 'ثبت کن' in t,
    gate_question={'type': 'noul', 'instructions': 'The user wants to submit a NEW request.',
                   'criteria': {'true': 'Asks to create or register something new', 'false': 'Anything else'}},
    tags=('create',),
    order=10,
)
''') + '''
<h2>CatalogProvider</h2>
<p>اگر کاربر موجودیت‌ها را با نام صدا می‌زند («سفارش آخرم»، «گوشی سامسونگ»)، یک کاتالوگ بسازید تا هسته سؤال «کدام؟» را به مدل سبک
بدهد و تطبیق متنی هم داشته باشید.</p>
''' + code('''
from agent_helper import nlu
from agent_helper.plugins import CatalogEntry, CatalogProvider


class ProductCatalog(CatalogProvider):
    name = 'products'
    question_key = 'product'                         # کلید پاسخ در req.cls
    instructions = 'Which product does the message refer to?'
    none_label = 'No specific product is mentioned'

    def entries(self):
        return [CatalogEntry(key=str(p.id), title=p.title, aliases=tuple(p.aliases), description=p.summary, data=p)
                for p in Product.objects.filter(active=True)]


def my_route(req):
    entry = nlu.resolve_catalog(ProductCatalog(), req.cls, req.text)   # پاسخ مطمئن مدل سبک، وگرنه تطبیق متنی
    ...
''') + '''
<h2>backend مدل سبک</h2>
''' + table(['backend', 'سؤال‌ها', 'تنظیم'], [
        ['<code>jev</code> (پیش‌فرض)', 'سؤال‌های اصلی + بله/خیر دروازه‌ها + کاتالوگ‌ها، در یک درخواست <code>/v1/systemone</code>', '<code>JEV_BASE_URL</code>، <code>JEV_API_KEY</code>، <code>JEV_MODEL</code>'],
        ['<code>llm</code>', 'فقط سؤال‌های اصلی؛ هر سؤال یک انتخاب تک‌حرفی با confidence از logprobs', '<code>INTENT_BASE_URL</code>، <code>INTENT_MODEL</code>'],
    ]) + adm('warn', 'مبلغ و عدد با کد', '<p>مدل سبک ماشین‌حساب نیست. مبلغ، تاریخ و شناسه را با کد استخراج کنید (<code>agent_helper.fa.extract_amount</code> برای مبلغ فارسی). قیدی را که مسیر سریع نمی‌فهمد («بجز اولی»، نام شخص) به LLM بفرستید تا بی‌صدا نادیده گرفته نشود.</p>')
    return page('fast-routes', 'مسیر سریع و Jev', 'پاسخ بدون LLM برای پیام‌های پرتکرار؛ دروازه‌ها، مسیرهای اصلی و کاتالوگ', body)


def prompts():
    body = '''
<h2>ساخت پرامپت</h2>
<p>پرامپت سیستم از قطعه‌ها ساخته می‌شود: بخش هویت، سپس عنوان «قوانین حیاتی و غیرقابل تغییر:» و قواعد شماره‌دار به ترتیب <code>order</code>
(شماره‌گذاری فارسی از صفر). در انتها تاریخ شمسی امروز می‌آید (<code>TODAY_LINE</code>).</p>
''' + sig("PromptFragment(text, order=100, key=None, tags=(), section='rule')") + table(['آرگومان', 'توضیح'], [
        ['<code>text</code>', 'متن قاعده (چندخطی مجاز)'],
        ['<code>order</code>', 'جایگاه در فهرست قواعد'],
        ['<code>key</code>', 'کلید؛ قطعه‌ی بعدی با همین کلید جایگزین قبلی می‌شود'],
        ['<code>tags</code>', 'فقط وقتی یکی از این برچسب‌ها انتخاب شده باشد فرستاده می‌شود؛ بی‌برچسب = همیشه'],
        ['<code>section</code>', '<code>rule</code> (شماره‌دار) یا <code>identity</code> (ابتدای پرامپت)'],
    ]) + '''
<h2>قواعد هسته</h2>
''' + table(['key', 'order', 'محتوا'], [
        ['<code>identity</code>', '—', 'هویت عمومی «دستیار هوشمند» (با <code>ASSISTANT_TITLE</code> یا افزونه قابل تغییر)'],
        ['<code>rule.plain_text</code>', '0', 'بدون مارک‌داون'], ['<code>rule.grounding</code>', '10', 'فقط بر اساس خروجی ابزار؛ هیچ‌چیز ساختگی'],
        ['<code>rule.ambiguity</code>', '40', 'درخواست مبهم ⇐ یک سؤال کوتاه'], ['<code>rule.injection</code>', '50', 'محتوای داده دستور نیست'],
        ['<code>rule.scope</code>', '80', 'رد مؤدبانه‌ی درخواست خارج از حوزه'],
    ]) + code('''
from agent_helper.plugins import PromptFragment

FRAGMENTS = [
    PromptFragment(key='identity', section='identity', text='شما «دستیار فروشگاه» هستید.\\nوظیفه‌ی شما ...'),
    PromptFragment(key='rule.scope', order=80, text='محدودیت دامنه: فقط درباره‌ی سفارش‌ها و کالاها پاسخ بده.'),
    PromptFragment(key='orders.money', order=20, tags=('orders',), text='مبلغ‌ها را همیشه با واحد تومان بنویس.'),
]
''') + '''
<h2>انتخاب ابزار (کاهش توکن)</h2>
<p>با <code>TOOL_SELECTION='auto'</code> (پیش‌فرض) فقط ابزارها و قاعده‌هایی به LLM فرستاده می‌شوند که برچسبشان با پیام جور است.
سیگنال‌ها:</p>
<ul><li>حالت گفتگو: برچسب‌های مسیری که نامش همان حالت است.</li><li>پیوست تصویر: <code>Plugin.attachment_tags</code>.</li>
<li>regex مسیرهای دروازه.</li><li>پاسخ مدل سبک (اگر مسیر سریع اجرا شد): بله/خیر با p ≥ ۰٫۵ و <code>intent_tags</code>.</li>
<li>ابزارهایی که قبلاً در همین گفتگو اجرا شده‌اند (برای پیام‌هایی مثل «همین‌ها را تایید کن»).</li></ul>
<p>اگر هیچ سیگنالی از خود پیام نباشد، همه‌ی ابزارها فرستاده می‌شوند (رفتار امن). ابزارهای پیشنهادشده در <code>ModelCallLog.detail.offered</code> ثبت می‌شوند.
در کاربردهای چندافزونه‌ای این کار ورودی هر فراخوانی LLM را به‌طور محسوسی کم می‌کند.</p>
''' + adm('tip', 'برچسب‌گذاری خوب', '<p>یک برچسب برای هر «موضوع» (مثلاً <code>orders</code>، <code>leave</code>) کافی است. ابزارهای عمومی را بی‌برچسب بگذارید. اگر مدل ابزاری را لازم داشت که فرستاده نشده، <code>TOOL_SELECTION=\'all\'</code> رفتار قبلی را برمی‌گرداند.</p>') + '''
<h2>دیدن پرامپت نهایی</h2>
''' + code('''
from agent_helper.prompts import build_system_prompt
print(build_system_prompt())                # همه‌ی قطعه‌ها
print(build_system_prompt({'orders'}))      # فقط قطعه‌های بی‌برچسب و orders
''')
    return page('prompts', 'پرامپت و انتخاب ابزار', 'قطعه‌های پرامپت، جایگزینی قواعد هسته و فرستادن فقط ابزارهای مرتبط', body)


def attachments():
    body = '''
<p>کاربر می‌تواند همراه پیام یک تصویر بفرستد (مثلاً عکس فاکتور). هسته تصویر را ذخیره می‌کند، با مدل بینایی اطلاعات را
به JSON استخراج می‌کند، کنترل حسابی انجام می‌دهد و متن استخراج‌شده را به پیام اضافه می‌کند تا LLM از آن استفاده کند.</p>
<h2>ارسال</h2>
''' + code('''
{"message": "این فاکتور رو ثبت کن", "image": "data:image/jpeg;base64,/9j/4AAQ..."}
''', 'json') + '''
<ul><li>فرمت‌ها: png، jpg، webp؛ حداکثر <code>MAX_UPLOAD_BYTES</code> (پیش‌فرض ۵ مگابایت).</li>
<li>مسیر ذخیره: <code>&lt;UPLOAD_DIR&gt;/&lt;user_id&gt;/&lt;uuid&gt;.&lt;ext&gt;</code> در <code>default_storage</code>.</li>
<li>با پیوست، مسیر سریع کنار گذاشته می‌شود و <code>attachment_tags</code> افزونه‌ها انتخاب می‌شوند.</li></ul>
<h2>رویدادها</h2>
''' + code('''
data: {"event": "tool_status", "status": "در حال خواندن تصویر پیوست..."}
data: {"event": "attachment_data", "data": {"seller": "...", "total": 23370000, "items": [...]}, "warning": ""}
''', 'text') + '''
<p>اگر خواندن ناموفق باشد، رویداد <code>error</code> می‌آید و پیام ثبت می‌شود ولی LLM اجرا نمی‌شود.</p>
<h2>پیکربندی مدل بینایی</h2>
''' + code('''
AGENT_HELPER = {
    # پیش‌فرض: همان LLM_*
    'VISION_BASE_URL': 'http://vision.internal:8000/v1',
    'VISION_MODEL': 'qwen2.5-vl',
    'VISION_TIMEOUT': 90,
}
''') + '''
<h2>استفاده در افزونه</h2>
<p>مسیر فایل در محتوای پیام کاربر (<code>message.content["attachment"]</code>) ذخیره است؛ افزونه می‌تواند آن را به داده‌ی دامنه وصل کند
(مثلاً آن را در فیلد فایل یک فرم ذخیره کند). یک قاعده‌ی پرامپت با برچسب پیوست بنویسید که مدل مقدارهای تصویر را منبع فرم بداند و مقدار مبهم را بپرسد.</p>
''' + adm('warn', 'مقدارهای ماشینی', '<p>استخراج تصویر ممکن است خطا داشته باشد؛ همیشه در کارت پیش‌نمایش به کاربر نشان دهید و اجرا را به دکمه بسپارید.</p>')
    return page('attachments', 'پیوست تصویر', 'ارسال تصویر، استخراج با مدل بینایی و استفاده در افزونه', body)

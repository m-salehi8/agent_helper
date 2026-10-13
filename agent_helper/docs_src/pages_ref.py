from lib import adm, code, page, sig, table


def http_api():
    body = '''
<p>همه‌ی endpointها <code>IsAuthenticated</code> هستند و با کلاس‌های احراز هویت DRF پروژه‌ی شما کار می‌کنند (JWT، session، توکن).
مسیرها نسبت به جایی‌اند که <code>agent_helper.urls</code> را include کرده‌اید (در مثال‌ها <code>/api/assistant/</code>).</p>
''' + table(['روش', 'مسیر', 'نام URL', 'کار'], [
        ['POST', '<code>chat/</code>', '<code>assistant_chat</code>', 'ارسال پیام؛ پاسخ استریم SSE'],
        ['GET', '<code>conversations/</code>', '<code>assistant_conversations</code>', 'گفتگوهای کاربر'],
        ['GET', '<code>conversations/&lt;id&gt;/</code>', '<code>assistant_conversation_detail</code>', 'یک گفتگو با پیام‌ها'],
        ['POST', '<code>actions/&lt;id&gt;/confirm/</code>', '<code>assistant_action_confirm</code>', 'اجرای اقدام معلق'],
        ['POST', '<code>actions/&lt;id&gt;/cancel/</code>', '<code>assistant_action_cancel</code>', 'لغو اقدام معلق'],
    ]) + '''
<h2>POST chat/</h2>
''' + table(['فیلد', 'نوع', 'توضیح'], [
        ['<code>message</code>', 'string، اجباری، حداکثر ۵۰۰۰', 'متن کاربر'],
        ['<code>conversation_id</code>', 'int، اختیاری', 'ادامه‌ی گفتگوی قبلی (فقط گفتگوی خود کاربر؛ وگرنه ۴۰۴)؛ خالی = گفتگوی جدید'],
        ['<code>image</code>', 'data URL، اختیاری', 'تصویر png/jpg/webp (<a href="attachments.html">پیوست تصویر</a>)'],
    ]) + code('''
POST /api/assistant/chat/
Authorization: Bearer eyJ...
Content-Type: application/json

{"message": "سفارش‌های باز من را نشان بده", "conversation_id": 12}
''', 'http') + '''
<p>پاسخ <code>200 text/event-stream</code> است؛ هر رویداد یک خط <code>data: &lt;JSON&gt;</code> و یک خط خالی. هدرهای
<code>Cache-Control: no-cache</code> و <code>X-Accel-Buffering: no</code> برای عبور از nginx بدون بافر تنظیم می‌شوند.</p>
''' + table(['وضعیت', 'وقتی'], [
        ['<code>200</code>', 'استریم (حتی خطای LLM به‌صورت رویداد <code>error</code> می‌آید)'],
        ['<code>400</code>', 'بدنه‌ی نامعتبر (JSON خطای DRF)'], ['<code>401</code>', 'بدون احراز هویت'],
        ['<code>404</code>', '<code>conversation_id</code> مال کاربر نیست'],
        ['<code>429</code>', 'سقف دقیقه‌ای/روزانه یا تصویر نامعتبر؛ یک رویداد <code>error</code> با پیام فارسی'],
    ]) + '''
<h2>رویدادهای SSE</h2>
''' + table(['event', 'فیلدها', 'کاربرد در UI'], [
        ['<code>tool_status</code>', '<code>status</code>', 'نوار وضعیت («در حال …»)'],
        ['<code>token</code>', '<code>text</code>', 'متن پاسخ (فقط متن نهایی؛ متن قبل از فراخوانی ابزار نمایش داده نمی‌شود)'],
        ['<code>pending_action</code>', '<code>action_id</code>، <code>expires_at</code> + فیلدهای <code>preview</code>', 'کارت تایید/لغو'],
        ['<code>attachment_data</code>', '<code>data</code>، <code>warning</code>', 'کارت «خوانده‌شده از تصویر»'],
        ['<code>done</code>', '<code>conversation_id</code>، <code>message_id</code>، <code>path</code> (<code>fast</code> یا <code>llm</code>)', 'پایان؛ شناسه‌ی گفتگو را نگه دارید'],
        ['<code>error</code>', '<code>message</code> (+ <code>detail</code> در DEBUG)', 'هشدار'],
        ['رویدادهای افزونه', 'آزاد (از <code>ToolSpec.events</code>)', 'جدول، کارت وضعیت، …'],
    ]) + code('''
data: {"event": "tool_status", "status": "در حال جستجوی سفارش‌ها..."}

data: {"event": "order_list", "items": [{"id": 5, "total": 120000}], "count": 1}

data: {"event": "token", "text": "یک سفارش باز دارید."}

data: {"event": "done", "conversation_id": 12, "message_id": 88, "path": "fast"}
''', 'text') + '''
<h3>پیام‌های خطا</h3>
''' + table(['حالت', 'message'], [
        ['timeout مدل', 'زمان پاسخگویی سرویس مدل هوش مصنوعی به پایان رسید (Timeout)…'],
        ['۴۲۹ مدل', 'سرویس هوش مصنوعی در حال حاضر شلوغ است…'], ['۴۰۱/۴۰۳ مدل', 'خطای اعتبارسنجی کلید API…'],
        ['سایر HTTP', 'خطایی در ارتباط با سرور هوش مصنوعی رخ داد…'], ['اتصال/تنظیم نشده', 'امکان برقراری ارتباط با ارائه‌دهنده… میسر نشد.'],
    ]) + '''
<h2>POST actions/&lt;id&gt;/confirm/</h2>
<p>بدنه‌ی دلخواه (JSON) که بی‌تغییر به <code>ActionKind.execute</code> به‌عنوان <code>params</code> داده می‌شود.</p>
''' + code('''
POST /api/assistant/actions/45/confirm/
{"node_ids": [1024, 1031], "unchecked": "keep"}

200 {"message": "۲ مورد تأیید شد.", "action_id": 45, "status": "confirmed",
     "results": [{"node_id": 1024, "status": "success", "detail": "..."}]}
''', 'http') + table(['وضعیت', 'بدنه'], [
        ['<code>200</code>', 'نتیجه‌ی اجرا؛ تایید دوباره: <code>{"already_confirmed": true, "status", "results"}</code>'],
        ['<code>400</code>', '<code>{"error"}</code>: منقضی، وضعیت غیر pending، نوع ناشناخته یا پارامتر نامعتبر'],
        ['<code>403</code>', 'اقدام مال کاربر دیگری است'], ['<code>404</code>', 'اقدام وجود ندارد'],
        ['<code>500</code>', 'اجراکننده خطا داد؛ اقدام <code>failed</code> و ممیزی شد'],
    ]) + '''
<h2>POST actions/&lt;id&gt;/cancel/</h2>
''' + code('''
200 {"message": "اقدام با موفقیت لغو شد.", "status": "cancelled", "action_id": 45}
''', 'http') + '''
<h2>GET conversations/</h2>
''' + code('''
[{"id": 12, "title": "سفارش‌های باز من را نشان بده", "created_at": "1405-07-20 14:02:11", "messages_count": 4}]
''', 'json') + code('''
GET conversations/12/
{"id": 12, "title": "...", "created_at": "...",
 "messages": [{"id": 87, "role": "user", "content": {"text": "..."}, "created_at": "..."},
              {"id": 88, "role": "assistant", "content": {"text": "..."}, "created_at": "..."}]}
''', 'json') + adm('note', 'صفحه‌بندی', '<p>فهرست گفتگوها از تنظیم <code>DEFAULT_PAGINATION_CLASS</code> پروژه پیروی می‌کند.</p>')
    return page('http-api', 'API و رویدادهای SSE', 'endpointها، بدنه‌ها، کدهای وضعیت و همه‌ی رویدادهای استریم', body)


def frontend():
    body = '''
<p><code>EventSource</code> فقط GET می‌فرستد؛ برای POST با هدر احراز هویت از <code>fetch</code> و خواندن استریم استفاده کنید.</p>
<h2>کلاینت مرورگر</h2>
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
chat('سفارش‌هایم را نشان بده', conversationId, TOKEN, ev => {
  if (ev.event === 'token') appendText(ev.text);
  else if (ev.event === 'tool_status') showStatus(ev.status);
  else if (ev.event === 'pending_action') renderActionCard(ev);
  else if (ev.event === 'error') showError(ev.message);
  else if (ev.event === 'done') conversationId = ev.conversation_id;
});
''', 'js') + '''
<h2>کارت اقدام</h2>
''' + code('''
function renderActionCard(ev) {
  // ev.kind و فیلدهای preview را نمایش بدهید
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
<h2>نکته‌ها</h2>
<ul><li>بعد از <code>done</code> شناسه‌ی گفتگو را نگه دارید تا پیام بعدی ادامه‌ی همان گفتگو باشد.</li>
<li>تا رسیدن <code>done</code> یا <code>error</code> دکمه‌ی ارسال را غیرفعال کنید.</li>
<li>کارت را بعد از <code>expires_at</code> غیرفعال کنید؛ سرور هم اقدام منقضی را رد می‌کند.</li>
<li>رویدادهای ناشناخته را نادیده بگیرید تا افزونه‌ی تازه کلاینت را نشکند.</li>
<li>پشت nginx: <code>proxy_buffering off</code> یا همان هدر <code>X-Accel-Buffering: no</code> که سرور می‌فرستد.</li></ul>
<h2>Python (اسکریپت یا تست یکپارچه)</h2>
''' + code('''
import json, requests

with requests.post(url + '/api/assistant/chat/', json={'message': 'سلام'},
                   headers={'Authorization': 'Bearer ' + token}, stream=True) as r:
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith('data: '):
            print(json.loads(line[6:]))
''')
    return page('frontend', 'اتصال رابط کاربری', 'خواندن استریم SSE با fetch، کارت اقدام و نکته‌های استقرار', body)


def python_api():
    rows = [
        ('agent_helper', [
            ('register(plugin)', 'ثبت یک Plugin (در AppConfig.ready)'),
        ]),
        ('agent_helper.plugins', [
            ('Plugin, ToolSpec, ActionKind, FastRoute, PromptFragment', 'قرارداد افزونه (صفحه‌های راهنما)'),
            ('CatalogProvider, CatalogEntry(key, title, aliases=(), description=\'\', data=None)', 'کاتالوگ'),
            ('ToolContext(user, conversation, trace, proposed).propose(kind, payload, minutes=None)', 'زمینه‌ی ابزار'),
            ('RouteRequest, Defer(reason)', 'ورودی و نتیجه‌ی مسیر سریع'),
        ]),
        ('agent_helper.registry', [
            ('registry.tools() / tool(name) / actions() / action(kind) / routes() / catalogs() / fragments() / check()', 'جست‌وجو در افزونه‌های ثبت‌شده'),
            ('override(plugins)', 'context manager: جایگزینی موقت افزونه‌ها (تست)'),
        ]),
        ('agent_helper.tools', [
            ('execute_tool(name, arguments, user, conversation=None, ctx=None) -> dict', 'اجرای یک ابزار برای user'),
            ('run_logged(trace, name, args, user, conversation=None, collect=None)', 'اجرا با لاگ؛ پیشنهادها در collect'),
            ('specs(names=None), anthropic_schemas(selected=None), openai_schemas(selected=None), set_mode(conversation, mode)', ''),
        ]),
        ('agent_helper.actions', [
            ('create_pending(user, conversation, kind, payload, minutes=None) -> PendingAction', 'ساخت پیشنهاد'),
            ('pending_event(action) -> dict', 'رویداد SSE کارت'),
            ('confirm_pending_action(user, action_id, params=None) -> dict', 'همان منطق endpoint تایید (با status_code)'),
            ('cancel_pending_action(user, action_id) -> dict', 'لغو'),
            ('audit(user, action, status, detail=\'\', **refs)', 'ردیف ممیزی'),
        ]),
        ('agent_helper.llm', [
            ('run_assistant_agent(user, conversation, user_prompt, provider=None, attachment=None)', 'generator رویدادها؛ همان چیزی که view استریم می‌کند'),
            ('get_llm_provider()', 'ارائه‌دهنده از روی تنظیمات'),
            ('OpenAICompatibleProvider, AnthropicProvider, MockProvider(responses)', 'ارائه‌دهنده‌ها'),
            ('LLMResponse(text=None, tool_calls=[], raw={}), ToolCall(id, name, arguments)', 'پاسخ مدل'),
        ]),
        ('agent_helper.router', [('try_fast_path(user, conversation, text, trace=None)', 'پاسخ مسیر سریع یا None'), ('enabled()', '')]),
        ('agent_helper.nlu', [
            ('classify(text), jev_classify(text, timeout), llm_classify(text, timeout)', 'مدل سبک'),
            ('main_questions(), gate_questions(), jev_questions(), catalog_question(provider)', 'سؤال‌های جمع‌شده از افزونه‌ها'),
            ('match_catalog(provider, text, stopwords=()), resolve_catalog(provider, cls, text, stopwords=())', 'تطبیق کاتالوگ'),
            ('JevError', ''),
        ]),
        ('agent_helper.prompts', [('build_system_prompt(tags=None), fragments(), CORE_FRAGMENTS', '')]),
        ('agent_helper.selection', [('select_tags(conversation, text, attachment=None, cls=None), select_tools(tags)', 'انتخاب ابزار')]),
        ('agent_helper.fa', [('extract_amount(text), extract_currency(text), normalize(text), to_ascii_digits(s), fa_number(n)', 'متن و عدد فارسی')]),
        ('agent_helper.vision', [('save_upload(user, data_url) -> path, extract_document(path, trace=None), check_totals(data)', 'پیوست تصویر')]),
        ('agent_helper.conf', [('get(key), flag(key), daily_limit(), DEFAULTS', 'تنظیمات')]),
        ('agent_helper.testing', [('make_user(username), fast_router(on=True, **env)', 'کمک‌های تست')]),
        ('agent_helper.trace', [('RequestTrace(user, conversation, message)', 'لاگ یک درخواست: model_call, run_tool, finish')]),
        ('agent_helper.views', [('ChatStreamView, ConversationListView, ConversationDetailView, ActionConfirmView, ActionCancelView, check_rate_limits(user)', 'view ها')]),
        ('agent_helper.models', [('AssistantConversation, AssistantMessage, PendingAction, ActionAuditLog, AssistantRequestLog, ModelCallLog, ToolCallLog', 'نام‌های دیگر: Conversation, Message, RequestLog')]),
    ]
    body = ''
    for mod, items in rows:
        body += f'<h2><code>{mod}</code></h2>' + ''.join(sig(s) + (f'<p>{d}</p>' if d else '') for s, d in items)
    body += adm('note', 'پایداری', '<p>قرارداد افزونه (<code>agent_helper.plugins</code>، <code>register</code>، <code>actions.audit</code>، <code>actions.create_pending</code>) API پایدار است. بقیه‌ی ماژول‌ها داخلی‌اند و ممکن است در نسخه‌های بعد تغییر کنند.</p>')
    return page('python-api', 'مرجع پایتون', 'ماژول‌ها، توابع و کلاس‌های عمومی', body)


def settings_ref():
    import ast, os
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'agent_helper', 'conf.py'), encoding='utf-8').read()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'DEFAULTS')
    defaults = eval(compile(ast.Expression(node.value), 'conf.py', 'eval'))  # literal dict (with arithmetic)
    desc = {
        'LLM_PROVIDER': '<code>openai</code> (هر سرور سازگار) یا <code>anthropic</code>', 'LLM_BASE_URL': 'نشانی سرور LLM (بدون آن مسیر LLM خطا می‌دهد)',
        'LLM_API_KEY': 'کلید', 'LLM_MODEL': 'نام مدل', 'LLM_TIMEOUT': 'ثانیه', 'MAX_AGENT_ITERATIONS': 'حداکثر دور حلقه‌ی ابزار',
        'USE_FAST_ROUTER': 'روشن‌کردن مسیر سریع (<code>1</code>)', 'FAST_THRESHOLD': 'حداقل اطمینان مسیر سریع',
        'INTENT_BACKEND': '<code>jev</code> یا <code>llm</code>', 'INTENT_TIMEOUT': 'مهلت Jev (ثانیه)',
        'INTENT_BASE_URL': 'سرور مدل لوکال تشخیص نیت (پیش‌فرض LLM)', 'INTENT_API_KEY': '', 'INTENT_MODEL': '',
        'JEV_BASE_URL': 'سرور Jev (<code>/v1/systemone</code>)', 'JEV_API_KEY': '', 'JEV_MODEL': '',
        'VISION_BASE_URL': 'سرور مدل بینایی (پیش‌فرض LLM)', 'VISION_API_KEY': '', 'VISION_MODEL': '', 'VISION_TIMEOUT': 'ثانیه',
        'UPLOAD_DIR': 'پوشه‌ی تصویرها در storage', 'MAX_UPLOAD_BYTES': 'حداکثر حجم تصویر',
        'PER_MINUTE_LIMIT': 'سقف پیام در دقیقه برای هر کاربر', 'DAILY_LIMIT': 'سقف روزانه (None ⇐ <code>settings.ASSISTANT_DAILY_LIMIT</code> یا ۱۰۰)',
        'ACTION_EXPIRES_MINUTES': 'عمر پیش‌فرض اقدام معلق', 'TOOL_SELECTION': '<code>auto</code> یا <code>all</code>',
        'REGISTER_ADMIN': 'ثبت ادمین مدل‌ها', 'ADMIN_BASE': 'کلاس پایه‌ی ModelAdmin', 'ADMIN_INLINE_BASE': 'کلاس پایه‌ی inline',
        'ASSISTANT_TITLE': 'نام دستیار در پرامپت', 'ASSISTANT_MISSION': 'جمله‌ی مأموریت در پرامپت', 'TODAY_LINE': 'تاریخ شمسی امروز در پرامپت',
    }
    rows = [[f'<code>{k}</code>', f'<code>{env}</code>' if env else '—', f'<code>{default!r}</code>', desc.get(k, '')]
            for k, (env, default) in defaults.items()]
    rows.append(['<code>TEST_USER_FACTORY</code>', '—', '<code>None</code>', 'مسیر تابع <code>(username) -&gt; user</code> برای <code>testing.make_user</code>'])
    body = '''
<p>همه در <code>settings.AGENT_HELPER</code>. ترتیب: settings ⇐ متغیر محیطی ⇐ پیش‌فرض. مقدارهای متغیر محیطی به نوع پیش‌فرض تبدیل می‌شوند (عدد، بولی).</p>
''' + table(['کلید', 'متغیر محیطی', 'پیش‌فرض', 'توضیح'], rows) + '''
<h2>تنظیمات Django مرتبط</h2>
''' + table(['تنظیم', 'اثر'], [
        ['<code>AUTH_USER_MODEL</code>', 'همه‌ی FKها به مدل کاربر پروژه'],
        ['<code>REST_FRAMEWORK</code>', 'احراز هویت و صفحه‌بندی endpointها'],
        ['<code>CACHES</code>', 'شمارنده‌های سقف نرخ (در چند پروسه از Redis/Memcached استفاده کنید)'],
        ['<code>DEFAULT_FILE_STORAGE</code> / <code>STORAGES</code>', 'محل ذخیره‌ی تصویرهای پیوست'],
        ['<code>MIGRATION_MODULES</code>', 'فقط برای نصب روی جدول‌های قدیمی (<a href="deployment.html">استقرار</a>)'],
    ])
    return page('settings-ref', 'مرجع تنظیمات', 'همه‌ی کلیدهای AGENT_HELPER با متغیر محیطی و پیش‌فرض', body)

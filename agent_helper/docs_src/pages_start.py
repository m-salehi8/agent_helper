from lib import adm, code, page, sig, table


def index():
    body = '''
<p><b>agent-helper</b> یک اپ Django برای ساختن دستیار گفتگومحور روی داده‌های سامانه‌ی خودتان است. هسته‌ی آن هیچ دامنه‌ای
را نمی‌شناسد؛ هر کاربرد (سفارش، یادداشت، درخواست‌های اداری، …) یک <b>افزونه</b> است که ابزارها، اقدام‌ها و قواعد خودش را ثبت می‌کند.</p>
<div class="cards">
<a href="tutorial.html"><b>🚀 شروع سریع</b><span>از یک پروژه‌ی خالی Django تا اولین گفتگو در ۱۰ دقیقه</span></a>
<a href="plugins.html"><b>🧩 نوشتن افزونه</b><span>ابزار، اقدام معلق، مسیر سریع و قاعده‌ی پرامپت</span></a>
<a href="http-api.html"><b>📡 API و SSE</b><span>endpointها، رویدادها و نمونه‌ی درخواست و پاسخ</span></a>
<a href="security.html"><b>🛡️ مدل امنیتی</b><span>چرا مدل هیچ‌وقت خودش چیزی را اجرا نمی‌کند</span></a>
</div>
<h2>چه چیزی آماده است</h2>
<ul>
<li><b>حلقه‌ی عامل با ابزار</b> روی هر سرور سازگار با OpenAI (vLLM، llama.cpp، …) یا Anthropic؛ حداکثر ۶ دور.</li>
<li><b>مسیر سریع بدون LLM:</b> regex و یک فراخوانی مدل سبک (Jev یا مدل لوکال با logprobs) برای پیام‌های پرتکرار؛ هر تردید ⇐ LLM.</li>
<li><b>اقدام معلق:</b> مدل فقط «پیشنهاد» می‌سازد؛ اجرا فقط با دکمه‌ی کاربر، با قفل، مهلت، idempotent و ممیزی.</li>
<li><b>استریم SSE</b> برای متن، وضعیت ابزار، کارت‌ها و خطا.</li>
<li><b>پیوست تصویر</b> (مثلاً فاکتور) با مدل بینایی و کنترل حسابی.</li>
<li><b>لاگ کامل:</b> هر پیام، هر فراخوانی مدل و هر ابزار با زمان و توکن؛ ادمین آماده.</li>
<li><b>کاهش توکن:</b> فقط ابزارها و قاعده‌های مرتبط با پیام به مدل داده می‌شود.</li>
<li><b>سقف نرخ</b> دقیقه‌ای و روزانه برای هر کاربر.</li>
<li><b>آفلاین:</b> هیچ نشانی پیش‌فرضی به اینترنت اشاره نمی‌کند؛ همه‌چیز با URL قابل تنظیم است.</li>
</ul>
<h2>یک نگاه سریع</h2>
''' + code('''
# myplugin/plugin.py
from agent_helper.plugins import Plugin, ToolSpec

def list_orders(user, args, ctx):
    return {'orders': [{'id': o.id, 'total': o.total} for o in user.orders.all()[:20]]}

PLUGIN = Plugin(name='orders', tools=[
    ToolSpec('list_orders', 'فهرست سفارش‌های کاربر', {'type': 'object', 'properties': {}}, list_orders),
])
''') + '''
<p>کاربر می‌نویسد «سفارش‌هایم را نشان بده»، مدل ابزار <code>list_orders</code> را صدا می‌زند (همیشه برای <code>request.user</code>) و پاسخ به‌صورت SSE به رابط کاربری می‌رسد.</p>
<h2>پکیج‌ها</h2>
''' + table(['پکیج', 'نقش'], [
        ['<code>agent-helper</code>', 'هسته (همین مستندات)'],
        ['<code>agent-helper-demo</code>', 'افزونه‌ی نمونه‌ی «یادداشت و مرخصی» و پروژه‌ی مستقل؛ بهترین نقطه‌ی شروع برای خواندن کد'],
    ]) + '''
<h2>نیازمندی‌ها</h2>
<ul><li>Python ≥ 3.10، Django ≥ 4.2، Django REST framework ≥ 3.14</li><li>django-jalali و jdatetime (تاریخ‌های شمسی)، requests</li>
<li>یک سرور مدل زبانی با پشتیبانی tool calling (برای مسیر LLM)</li><li>اختیاری: Jev یا یک مدل لوکال با logprobs برای مسیر سریع؛ مدل بینایی برای پیوست تصویر</li></ul>
'''
    return page('index', 'agent-helper', 'دستیار هوشمند افزونه‌پذیر برای Django: LLM با ابزار، مسیر سریع بدون LLM و اقدام‌هایی که فقط کاربر اجرا می‌کند', body)


def installation():
    body = '''
<h2>نصب از wheel (آفلاین)</h2>
<p>سرورهای عملیاتی معمولاً اینترنت ندارند؛ wheelها و وابستگی‌ها را روی ماشین توسعه آماده کنید و همراه ببرید.</p>
<ol class="steps">
<li><b>ساخت wheel پکیج‌ها</b> (بدون اینترنت):''' + code('''
cd packages
pip wheel --no-deps --no-build-isolation --no-index -w dist ./agent_helper ./agent_helper_demo
''', 'bash') + '''</li>
<li><b>جمع‌کردن وابستگی‌ها</b> (یک‌بار، روی ماشینی با دسترسی):''' + code('''
pip download --only-binary=:all: -d wheelhouse \\
    Django==5.0.4 djangorestframework==3.15.1 django-jalali==6.2.1 jdatetime==5.0.0 requests==2.32.3
''', 'bash') + '''</li>
<li><b>نصب روی سرور:</b>''' + code('''
pip install --no-index --find-links wheelhouse --find-links dist --pre agent-helper
''', 'bash') + '''</li></ol>
''' + adm('note', 'نسخه‌ی بتا', '<p>نسخه‌ی فعلی پیش‌انتشار است (<code>0.1.0b1</code>)؛ pip آن را فقط با <code>--pre</code> یا نسخه‌ی دقیق (<code>agent-helper==0.1.0b1</code>) انتخاب می‌کند.</p>') + adm('tip', 'نسخه‌ها', '<p>نسخه‌های بالا همان‌هایی است که تست شده‌اند. نسخه‌ی پایتون ماشین دانلود و سرور باید یکی باشد (wheelهای باینری مثل <code>charset-normalizer</code>).</p>') + '''
<h2>نصب از سورس (توسعه)</h2>
''' + code('''
pip install -e packages/agent_helper
# یا بدون نصب: مسیر packages/agent_helper را به sys.path اضافه کنید
''', 'bash') + '''
<h2>افزودن به پروژه</h2>
''' + code('''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'django_jalali',
    'agent_helper',
    'myplugin',            # افزونه‌ی شما
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
<h2>بررسی نصب</h2>
''' + code('''
python manage.py check            # خطای agent_helper.E001 یعنی ابزاری به اقدام ثبت‌نشده اشاره می‌کند
python manage.py test agent_helper
''', 'bash') + '''
<p>جدول‌هایی که ساخته می‌شوند: گفتگو، پیام، اقدام معلق، ممیزی، لاگ درخواست، لاگ مدل و لاگ ابزار (فهرست کامل در <a href="concepts.html">مفاهیم</a>).</p>
'''
    return page('installation', 'نصب', 'نصب آفلاین با wheel، افزودن به پروژه و migrate', body)


def tutorial():
    body = '''
<p>در این آموزش یک پروژه‌ی خالی می‌سازیم و افزونه‌ای به نام <code>notes</code> می‌نویسیم که یادداشت‌های کاربر را می‌خواند و
افزودن یادداشت را <b>پیشنهاد</b> می‌کند (ذخیره فقط با دکمه‌ی کاربر). کد کامل مشابه همین در پکیج <code>agent-helper-demo</code> هست.</p>
<h2>۱. پروژه و نصب</h2>
''' + code('''
python -m venv venv && . venv/bin/activate
pip install --no-index --find-links wheelhouse --find-links dist --pre agent-helper
django-admin startproject mysite . && python manage.py startapp notes
''', 'bash') + '''
<h2>۲. مدل داده‌ی دامنه</h2>
''' + code('''
# notes/models.py
from django.conf import settings
from django.db import models

class Note(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
''') + '''
<h2>۳. افزونه</h2>
''' + code('''
# notes/plugin.py
from agent_helper import actions
from agent_helper.plugins import ActionKind, Plugin, PromptFragment, ToolSpec


def list_my_notes(user, args, ctx):
    """فقط‌خواندنی؛ user همیشه request.user است"""
    from notes.models import Note
    notes = Note.objects.filter(user=user).order_by('-id')[:10]
    return {'count': len(notes), 'notes': [{'id': n.id, 'text': n.text} for n in notes]}


def propose_add_note(user, args, ctx):
    """فقط پیشنهاد؛ چیزی ذخیره نمی‌شود"""
    text = str(args.get('text') or '').strip()
    if not text:
        return {'error': 'متن یادداشت خالی است.'}
    action = ctx.propose('add_note', {'text': text})
    return {'status': 'ready', 'action_id': action.id,
            'message': 'پیش‌نویس آماده است؛ کاربر باید دکمه را بزند. نگو ذخیره شد.'}


def execute_add_note(user, action, params):
    """فقط از endpoint تایید، داخل تراکنش و با قفل"""
    from notes.models import Note
    note = Note.objects.create(user=user, text=action.payload['text'])
    actions.audit(user, action, 'created', 'یادداشت ذخیره شد', node_id=note.id)
    return {'status': 'confirmed', 'message': 'یادداشت ذخیره شد.',
            'results': [{'note_id': note.id, 'status': 'success'}], 'status_code': 200}


PLUGIN = Plugin(
    name='notes',
    tools=[
        ToolSpec('list_my_notes', 'فهرست یادداشت‌های کاربر',
                 {'type': 'object', 'properties': {}}, list_my_notes,
                 status='در حال خواندن یادداشت‌ها...'),
        ToolSpec('propose_add_note', 'پیش‌نویس یادداشت جدید (ذخیره نمی‌کند)',
                 {'type': 'object', 'properties': {'text': {'type': 'string'}}, 'required': ['text']},
                 propose_add_note, read_only=False, proposes='add_note'),
    ],
    actions=[ActionKind('add_note', execute=execute_add_note,
                        preview=lambda p: {'kind': 'add_note', 'text': p['text']},
                        propose_schema={'type': 'object', 'required': ['text']})],
    prompt_fragments=[PromptFragment(
        'یادداشت‌ها: برای دیدن list_my_notes و برای افزودن propose_add_note؛ هرگز نگو ذخیره شد.', order=60)],
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
<h2>۴. تنظیمات و URL</h2>
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
<h2>۵. اولین گفتگو</h2>
<p>با کاربری که وارد شده (یا توکن JWT اگر پروژه‌تان JWT دارد):</p>
''' + code('''
curl -N -X POST http://127.0.0.1:8000/api/assistant/chat/ \\
     -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' \\
     -d '{"message": "یادداشت کن فردا ساعت ۱۰ جلسه دارم"}'
''', 'bash') + code('''
data: {"event": "tool_status", "status": "در حال اجرای ابزار propose_add_note..."}

data: {"event": "pending_action", "action_id": 7, "kind": "add_note", "text": "فردا ساعت ۱۰ جلسه", "expires_at": "1405/07/20 14:10"}

data: {"event": "token", "text": "پیش‌نویس یادداشت آماده است؛ برای ذخیره دکمه‌ی تایید را بزنید."}

data: {"event": "done", "conversation_id": 3, "message_id": 12, "path": "llm"}
''', 'text') + '''
<p>کاربر دکمه را می‌زند و رابط کاربری تایید را می‌فرستد:</p>
''' + code('''
curl -X POST http://127.0.0.1:8000/api/assistant/actions/7/confirm/ -H 'Authorization: Bearer <token>'
# {"status": "confirmed", "message": "یادداشت ذخیره شد.", "results": [...]}
''', 'bash') + '''
<h2>۶. تست</h2>
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
            LLMResponse(tool_calls=[ToolCall(id='1', name='propose_add_note', arguments={'text': 'سلام'})]),
            LLMResponse(text='دکمه را بزنید.'),
        ])
        with override([PLUGIN]), fast_router(on=False):
            events = list(run_assistant_agent(user, conv, 'یادداشت کن سلام', provider=provider))
        self.assertTrue(any(e['event'] == 'pending_action' for e in events))
        self.assertFalse(user.notes.exists())
''') + '''
''' + adm('tip', 'بعدی چه؟', '<p><a href="fast-routes.html">مسیر سریع</a> برای پیام‌های پرتکرار بدون LLM، <a href="frontend.html">اتصال رابط کاربری</a> و <a href="deployment.html">استقرار</a>.</p>')
    return page('tutorial', 'آموزش: از صفر تا اولین گفتگو', 'یک پروژه‌ی خالی، یک افزونه‌ی کوچک با یک ابزار خواندنی و یک اقدام معلق، و اولین درخواست SSE', body)


def concepts():
    body = '''
<h2>مسیر یک پیام</h2>
<ol>
<li><b>ورود:</b> <code>POST chat/</code> با کاربر احرازشده؛ سقف نرخ (دقیقه‌ای/روزانه)؛ ذخیره‌ی پیوست تصویر اگر هست.</li>
<li><b>تصویر:</b> اگر پیوست دارد، مدل بینایی اطلاعات را استخراج می‌کند و متنش به پیام اضافه می‌شود (مسیر سریع کنار می‌رود).</li>
<li><b>مسیر سریع:</b> اگر روشن باشد: حالت گفتگو، regex مسیرها، یک فراخوانی مدل سبک، سپس مسیرهای افزونه‌ها. فقط با اطمینان ≥ آستانه پاسخ می‌دهد.</li>
<li><b>حلقه‌ی LLM:</b> سابقه‌ی گفتگو + ابزارهای مرتبط + پرامپت ساخته‌شده از قطعه‌ها؛ مدل ابزار صدا می‌زند تا پاسخ نهایی (حداکثر ۶ دور).</li>
<li><b>رویدادها:</b> هر مرحله SSE می‌شود؛ پیشنهادها کارت <code>pending_action</code> می‌سازند.</li>
<li><b>اجرا:</b> فقط وقتی کاربر دکمه را بزند: <code>POST actions/&lt;id&gt;/confirm/</code>.</li>
<li><b>لاگ:</b> یک ردیف لاگ درخواست + لاگ هر مدل و هر ابزار.</li>
</ol>
<h2>اجزای قرارداد افزونه</h2>
''' + table(['جزء', 'نقش', 'صفحه'], [
        ['<code>Plugin</code>', 'بسته‌ی همه‌ی اجزای یک افزونه؛ با <code>agent_helper.register</code> ثبت می‌شود', '<a href="plugins.html">نوشتن افزونه</a>'],
        ['<code>ToolSpec</code>', 'ابزاری که مدل یا مسیر سریع صدا می‌زند؛ فقط خواندن یا پیشنهاد', '<a href="tools.html">ابزارها</a>'],
        ['<code>ActionKind</code>', 'نوع اقدام معلق: پیش‌نمایش کارت و اجرای واقعی', '<a href="actions.html">اقدام معلق</a>'],
        ['<code>FastRoute</code>', 'مسیر بدون LLM (regex، سؤال بله/خیر، سؤال‌های اصلی)', '<a href="fast-routes.html">مسیر سریع</a>'],
        ['<code>CatalogProvider</code>', 'موجودیت‌هایی که کاربر با نام صدا می‌زند', '<a href="fast-routes.html">مسیر سریع</a>'],
        ['<code>PromptFragment</code>', 'قاعده‌ی پرامپت؛ می‌تواند قاعده‌ی هسته را جایگزین کند', '<a href="prompts.html">پرامپت</a>'],
    ]) + '''
<h2>مدل‌های داده</h2>
''' + table(['مدل', 'کاربرد'], [
        ['<code>AssistantConversation</code> (نام دیگر: <code>Conversation</code>)', 'گفتگوی هر کاربر؛ <code>mode</code> = حالت گفتگوی چندمرحله‌ای'],
        ['<code>AssistantMessage</code> (<code>Message</code>)', 'پیام‌های user / assistant؛ محتوا JSON (متن و مسیر پیوست)'],
        ['<code>PendingAction</code>', 'اقدام معلق: <code>kind</code>، <code>payload</code>، <code>status</code>، <code>expires_at</code>، <code>result</code>'],
        ['<code>ActionAuditLog</code>', 'ممیزی هر اجرای واقعی: کاربر، اقدام، شناسه‌ی مورد، وضعیت، توضیح'],
        ['<code>AssistantRequestLog</code> (<code>RequestLog</code>)', 'یک ردیف برای هر پیام: مسیر، دلیل، نیت، تعداد فراخوانی‌ها، توکن، مدت'],
        ['<code>ModelCallLog</code>', 'هر فراخوانی مدل (intent / chat / vision)'],
        ['<code>ToolCallLog</code>', 'هر اجرای ابزار با آرگومان و خلاصه‌ی نتیجه'],
    ]) + '''
<h2>وضعیت‌های اقدام معلق</h2>
''' + table(['وضعیت', 'معنی'], [
        ['<code>pending</code>', 'منتظر دکمه‌ی کاربر (پیش‌فرض ۱۰ دقیقه)'], ['<code>confirmed</code>', 'اجرا شد'],
        ['<code>partial</code>', 'بخشی از موارد اجرا شد'], ['<code>failed</code>', 'اجرا ناموفق (یا اجراکننده خطا داد)'],
        ['<code>cancelled</code>', 'کاربر لغو کرد یا هیچ موردی انتخاب نشد'], ['<code>expired</code>', 'مهلت گذشت؛ دیگر قابل تایید نیست'],
    ]) + '''
<h2>اصول طراحی</h2>
<ul><li><b>هوش مصنوعی پیشنهاد می‌دهد، انسان اجرا می‌کند.</b></li><li><b>همه‌چیز در محدوده‌ی کاربر جاری.</b></li>
<li><b>اول ارزان و سریع، بعد هوشمند؛</b> جواب غلط قطعی بدتر از جواب کند است.</li><li><b>قابل ردیابی:</b> هر تصمیم و فراخوانی لاگ می‌شود.</li></ul>
'''
    return page('concepts', 'مفاهیم و معماری', 'مسیر یک پیام، اجزای قرارداد افزونه، مدل‌های داده و وضعیت‌های اقدام', body)


def configuration():
    body = '''
<p>همه‌ی تنظیمات در یک دیکشنری <code>AGENT_HELPER</code> در <code>settings.py</code> هستند. هر کلید به این ترتیب خوانده می‌شود:</p>
<ol><li><code>settings.AGENT_HELPER[key]</code></li><li>متغیر محیطی متناظر (اگر دارد)</li><li>مقدار پیش‌فرض</li></ol>
<p>مقدارها در لحظه‌ی استفاده خوانده می‌شوند؛ پس تغییر متغیر محیطی در تست‌ها (<code>mock.patch.dict(os.environ)</code>) بلافاصله اثر دارد.</p>
<h2>حداقل تنظیم</h2>
''' + code('''
AGENT_HELPER = {
    'LLM_PROVIDER': 'openai',
    'LLM_BASE_URL': 'http://llm.internal:8000/v1',
    'LLM_MODEL': 'qwen3',
}
''') + '''
<h2>مسیر سریع با Jev</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'USE_FAST_ROUTER': '1',
    'INTENT_BACKEND': 'jev',
    'JEV_BASE_URL': 'http://jev.internal',     # همان قرارداد /v1/systemone
    'JEV_API_KEY': '...',
    'FAST_THRESHOLD': 0.8,
}
''') + '''
<h2>مسیر سریع با مدل لوکال</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'USE_FAST_ROUTER': '1',
    'INTENT_BACKEND': 'llm',                    # هر سرور OpenAI-compatible که logprobs بدهد
    'INTENT_BASE_URL': 'http://vllm.internal:8000/v1',
    'INTENT_MODEL': 'qwen3-1.7b',
}
''') + '''
<h2>با متغیرهای محیطی</h2>
''' + code('''
ASSISTANT_LLM_PROVIDER=openai
ASSISTANT_LLM_BASE_URL=http://llm.internal:8000/v1
ASSISTANT_LLM_API_KEY=...
ASSISTANT_LLM_MODEL=qwen3
ASSISTANT_USE_FAST_ROUTER=1
TYPESAFE_BASE_URL=http://jev.internal
TYPESAFE_API_KEY=...
''', 'bash') + '''
<h2>ادمین با قالب پروژه</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'ADMIN_BASE': 'myproject.admin.BaseModelAdmin',       # کلاس پایه‌ی ادمین پروژه
    'ADMIN_INLINE_BASE': 'myproject.admin.BaseTabularInline',
    # 'REGISTER_ADMIN': False,                             # هیچ ادمینی ثبت نشود
}
''') + '''
<h2>هویت دستیار در پرامپت</h2>
''' + code('''
AGENT_HELPER = {
    # ...
    'ASSISTANT_TITLE': 'دستیار فروشگاه',
    'ASSISTANT_MISSION': 'وظیفه‌ی شما پاسخ کوتاه و دقیق درباره‌ی سفارش‌های کاربر است.',
}
''') + '''
<p>فهرست کامل کلیدها در <a href="settings-ref.html">مرجع تنظیمات</a>.</p>
''' + adm('warn', 'بدون پیش‌فرض اینترنتی', '<p>اگر <code>LLM_BASE_URL</code> تنظیم نشده باشد، درخواست به LLM انجام نمی‌شود و کاربر پیام «امکان برقراری ارتباط… میسر نشد» می‌گیرد. Jev بدون <code>JEV_BASE_URL</code> خطا می‌دهد و پیام به LLM می‌رود.</p>')
    return page('configuration', 'پیکربندی', 'تنظیمات AGENT_HELPER، متغیرهای محیطی و نمونه‌های رایج', body)

from lib import adm, code, page, sig, table


def security():
    body = '''
<h2>ناپذیرها</h2>
<ol>
<li><b>دامنه‌ی کاربر:</b> ابزارها همیشه با <code>request.user</code> اجرا می‌شوند؛ هسته هرگز شناسه‌ی کاربر را از خروجی مدل نمی‌خواند و ابزار هم نباید.</li>
<li><b>پیشنهاد جدا از اجرا:</b> هیچ ابزار «اجرایی» وجود ندارد. ابزار غیر فقط‌خواندنی باید <code>proposes</code> داشته باشد و فقط PendingAction بسازد.</li>
<li><b>اجرا فقط با دکمه:</b> <code>confirm</code> با قفل <code>select_for_update</code>، بررسی مالکیت، وضعیت، مهلت؛ idempotent؛ داخل savepoint؛ با ممیزی.</li>
<li><b>مسیر سریع محافظه‌کار:</b> فقط با اطمینان ≥ آستانه؛ خطای مدل سبک یا LLM هرگز پاسخ غلط قطعی نمی‌سازد.</li>
<li><b>بدون اینترنت پیش‌فرض:</b> همه‌ی نشانی‌ها از تنظیمات.</li>
</ol>
<h2>تهدیدها و دفاع</h2>
''' + table(['تهدید', 'دفاع'], [
        ['کاربر داده‌ی کاربر دیگری را بخواهد («سفارش‌های آقای X»)', 'ابزار فقط داده‌ی <code>user</code> را برمی‌گرداند؛ مدل ابزاری برای کاربر دیگر ندارد'],
        ['تزریق دستور در پیام یا داده («دستورهای قبلی را فراموش کن»)', 'قاعده‌ی <code>rule.injection</code>؛ و حتی اگر مدل فریب بخورد ابزار اجرایی ندارد'],
        ['مدل ادعا کند کاری انجام شد', 'قاعده‌های پرامپت + اجرای واقعی فقط در endpoint دکمه'],
        ['تایید اقدام کاربر دیگر', 'بررسی مالکیت ⇐ ۴۰۳'], ['تایید دوباره / هم‌زمان', 'قفل ردیف + idempotent'],
        ['تغییر داده بین پیشنهاد و تایید', '<code>execute</code> دوباره بررسی می‌کند (مثلاً مبلغ)'],
        ['پیشنهاد قدیمی', 'مهلت (پیش‌فرض ۱۰ دقیقه) ⇐ <code>expired</code>'],
        ['سوءاستفاده‌ی حجمی', 'سقف دقیقه‌ای و روزانه برای هر کاربر'], ['فایل مخرب', 'فقط تصویر png/jpg/webp و سقف حجم'],
    ]) + '''
<h2>چک‌لیست بازبینی افزونه</h2>
<ul><li>هر کوئری ابزار با <code>user</code> فیلتر شده است؟</li><li>هیچ <code>save()</code>/<code>create()</code>/<code>delete()</code> در handler ابزار نیست؟</li>
<li><code>execute</code> payload را دوباره اعتبارسنجی می‌کند و به <code>params</code> فقط به‌عنوان انتخاب از همان payload اعتماد می‌کند؟</li>
<li>برای هر مورد اجراشده <code>actions.audit</code> نوشته می‌شود؟</li><li>تست «کاربر دیگر ⇐ ۴۰۳» و «پیشنهاد چیزی ذخیره نمی‌کند» دارید؟</li></ul>
''' + adm('note', 'لاگ و حریم خصوصی', '<p>متن پیام (کوتاه‌شده تا ۱۰۰۰ نویسه) و آرگومان ابزارها لاگ می‌شوند. اگر داده‌ی حساس دارید، دسترسی ادمین به لاگ‌ها را محدود کنید و برای پاک‌سازی دوره‌ای برنامه بگذارید.</p>')
    return page('security', 'مدل امنیتی', 'ناپذیرها، تهدیدها و چک‌لیست بازبینی افزونه', body)


def observability():
    body = '''
<h2>لاگ‌ها</h2>
''' + table(['مدل', 'یک ردیف برای', 'فیلدهای مهم'], [
        ['<code>AssistantRequestLog</code>', 'هر پیام کاربر', '<code>path</code> (fast/llm/error)، <code>fast_reason</code>، <code>intent</code>، <code>intent_confidence</code>، تعداد فراخوانی‌ها، توکن، <code>duration_ms</code>، <code>error</code>'],
        ['<code>ModelCallLog</code>', 'هر فراخوانی مدل', '<code>kind</code> (intent/chat/vision)، <code>model</code>، <code>ok</code>، <code>attempts</code>، توکن، مدت، <code>detail</code> (پاسخ‌های مدل سبک یا ابزارهای درخواستی و <code>offered</code>)'],
        ['<code>ToolCallLog</code>', 'هر اجرای ابزار', '<code>name</code>، <code>arguments</code>، <code>ok</code>، <code>result_summary</code>، مدت'],
        ['<code>ActionAuditLog</code>', 'هر اجرای واقعی', 'کاربر، اقدام، شناسه‌ی مورد، مبلغ، وضعیت، توضیح'],
    ]) + '''
<p>ثبت لاگ هرگز پاسخ را خراب نمی‌کند؛ خطای ذخیره‌ی لاگ فقط در logger هشدار می‌شود.</p>
<h2>دلیل‌های ارجاع به LLM (<code>fast_reason</code>)</h2>
''' + table(['مقدار', 'معنی'], [
        ['<code>disabled</code>', 'مسیر سریع خاموش است'], ['<code>&lt;mode&gt;_dialog</code>', 'گفتگو در حالت چندمرحله‌ای'],
        ['<code>&lt;route&gt;_request</code>', 'دروازه‌ی بدون handler (همیشه LLM)'], ['<code>classifier_error</code>', 'مدل سبک در دسترس نبود یا timeout'],
        ['<code>a_or_b_ambiguous</code>', 'دو دروازه هم‌زمان مطمئن'], ['<code>no_route</code>', 'هیچ مسیری پاسخ نداد'],
        ['سایر', 'دلیلی که <code>Defer</code> افزونه داده (مثلاً <code>low_intent_confidence</code>)'],
    ]) + '''
<h2>ادمین</h2>
<p>همه‌ی مدل‌ها در ادمین ثبت می‌شوند (فقط‌خواندنی). فهرست لاگ درخواست‌ها بالای جدول خلاصه‌ی فیلتر فعلی را نشان می‌دهد: سهم مسیر سریع، میانگین مدت هر مسیر و جمع توکن.</p>
''' + code('''
AGENT_HELPER = {'ADMIN_BASE': 'myproject.admin.BaseModelAdmin', 'ADMIN_INLINE_BASE': 'myproject.admin.BaseTabularInline'}
''') + '''
<h2>معیارهای پیشنهادی پایش</h2>
''' + code('''
from django.db.models import Avg, Count, Q, Sum
from agent_helper.models import AssistantRequestLog

AssistantRequestLog.objects.filter(created_at__gte=since).aggregate(
    total=Count('id'), fast=Count('id', filter=Q(path='fast')), errors=Count('id', filter=Q(status='error')),
    avg_llm_ms=Avg('duration_ms', filter=Q(path='llm')), tokens=Sum('input_tokens') + Sum('output_tokens'))

AssistantRequestLog.objects.values('fast_reason').annotate(n=Count('id')).order_by('-n')[:10]
''') + '''
<ul><li>نسبت مسیر سریع به LLM و دلیل‌های رایج ارجاع.</li><li>درصد خطای مدل (<code>ModelCallLog.ok=False</code>).</li>
<li>میانگین توکن مسیر LLM (اثر انتخاب ابزار).</li><li>اقدام‌های منقضی‌شده (پیشنهادهایی که کاربر تایید نکرد).</li></ul>
'''
    return page('observability', 'لاگ، ادمین و پایش', 'چه چیزی ثبت می‌شود و چطور ببینید', body)


def testing():
    body = '''
<h2>ابزارهای تست</h2>
''' + table(['ابزار', 'کار'], [
        ['<code>agent_helper.registry.override([PLUGIN])</code>', 'فقط افزونه‌های داده‌شده ثبت باشند'],
        ['<code>agent_helper.llm.MockProvider([LLMResponse(...), ...])</code>', 'LLM جعلی بدون شبکه؛ <code>call_history</code> درخواست‌ها را نگه می‌دارد'],
        ['<code>agent_helper.testing.fast_router(on=True, **env)</code>', 'روشن/خاموش کردن مسیر سریع در یک بلوک'],
        ['<code>mock.patch(\'agent_helper.nlu.classify\', return_value=...)</code>', 'پاسخ جعلی مدل سبک'],
        ['<code>agent_helper.testing.make_user(name)</code>', 'ساخت کاربر (با <code>TEST_USER_FACTORY</code> قابل سفارشی‌سازی)'],
    ]) + '''
<h2>حلقه‌ی عامل</h2>
''' + code('''
from agent_helper.llm import LLMResponse, MockProvider, ToolCall, run_assistant_agent

provider = MockProvider([
    LLMResponse(tool_calls=[ToolCall(id='1', name='list_orders', arguments={})]),
    LLMResponse(text='دو سفارش دارید.'),
])
with override([PLUGIN]), fast_router(on=False):
    events = list(run_assistant_agent(user, conversation, 'سفارش‌هایم', provider=provider))

assert events[-1]['event'] == 'done'
assert len(provider.call_history[0]['tools']) == 2          # ابزارهایی که مدل دید
''') + '''
<h2>مسیر سریع</h2>
''' + code('''
from unittest import mock
from agent_helper import router

answers = {'intent': {'choice': 'list', 'confidence': 0.95}}
with override([PLUGIN]), fast_router(), mock.patch('agent_helper.nlu.classify', return_value=answers):
    res = router.try_fast_path(user, None, 'سفارش‌هایم را نشان بده')
assert res['path'] == 'fast'
''') + '''
<h2>اقدام معلق و endpoint</h2>
''' + code('''
from rest_framework.test import APIRequestFactory, force_authenticate
from agent_helper import actions
from agent_helper.views import ActionConfirmView

action = actions.create_pending(user, None, 'cancel_order', {'order_id': order.id})
req = APIRequestFactory().post(f'/api/assistant/actions/{action.id}/confirm/', {}, format='json')
force_authenticate(req, user=other_user)
assert ActionConfirmView.as_view()(req, action_id=action.id).status_code == 403
''') + '''
<h2>اجرا</h2>
''' + code('''
python manage.py test agent_helper myplugin
# پروژه‌ی مستقل نمونه (بدون هیچ افزونه‌ی دیگری):
cd agent_helper_demo && python manage.py test agent_helper agent_helper_demo
''', 'bash') + adm('tip', 'تست جداسازی', '<p>هسته تستی دارد که import از پکیج‌های دامنه را ممنوع می‌کند. برای افزونه‌ی خودتان هم تست «پیشنهاد ذخیره نمی‌کند»، «کاربر دیگر ۴۰۳» و «تایید دوباره یک‌بار اجرا» بنویسید.</p>')
    return page('testing', 'تست', 'تست افزونه بدون شبکه: MockProvider، override، مسیر سریع و endpoint', body)


def deployment():
    body = '''
<h2>چک‌لیست</h2>
<ul><li>wheelها و <code>wheelhouse</code> روی سرور؛ <code>pip install --no-index --pre</code>.</li>
<li><code>migrate</code>.</li><li>نشانی‌های LLM، مدل سبک و بینایی در تنظیمات یا متغیر محیطی.</li>
<li>cache مشترک (Redis) برای سقف نرخ در چند پروسه.</li><li>nginx: بدون بافر برای مسیر <code>chat/</code>؛ timeout خواندن ≥ ۱۲۰ ثانیه.</li>
<li>سرور ASGI/WSGI با worker کافی: هر گفتگوی LLM یک worker را تا پایان استریم نگه می‌دارد.</li></ul>
''' + code('''
location /api/assistant/chat/ {
    proxy_pass http://app;
    proxy_buffering off;
    proxy_read_timeout 180s;
}
''', 'text') + '''
<h2>مدل خودمیزبان</h2>
<ul><li><b>LLM:</b> vLLM یا هر سرور OpenAI-compatible با tool calling؛ <code>LLM_PROVIDER=\'openai\'</code>. prefix caching توکن‌های تکراری پرامپت را ارزان می‌کند.</li>
<li><b>مدل سبک:</b> Jev یا هر سرور با همان قرارداد <code>/v1/systemone</code>) یا یک مدل کوچک با logprobs (<code>INTENT_BACKEND=\'llm\'</code>).</li>
<li><b>بینایی:</b> مدل VL روی همان سرور یا سرور جدا (<code>VISION_*</code>).</li></ul>
<p>بعد از تغییر مدل، ارزیابی مسیریابی و یک سناریوی کامل هر افزونه را دوباره اجرا کنید.</p>
<h2>نصب روی جدول‌های قدیمی (برچسب دیگر)</h2>
<p>اگر جدول‌ها از نسخه‌ای قبلی با برچسب اپ دیگری (مثلاً <code>assistant</code>) وجود دارند، بدون تغییر دیتابیس:</p>
''' + code('''
# myproject/agent_apps.py
from agent_helper.apps import AgentHelperConfig

class AssistantConfig(AgentHelperConfig):
    name = 'agent_helper'
    label = 'my_old_label'      # همان جدول‌ها، content typeها، مجوزها و نام URLهای ادمین

# settings.py
INSTALLED_APPS += ['myproject.agent_apps.AssistantConfig']
MIGRATION_MODULES = {'my_old_label': 'myproject.old_migrations'}   # تاریخچه‌ی migration موجود
''') + adm('warn', 'migration دستی', '<p>در این حالت <code>makemigrations</code> باید فقط روی برچسب قدیمی اجرا شود. migration اولیه‌ی خود پکیج (<code>agent_helper/migrations</code>) برای نصب تازه است.</p>') + '''
<h2>به‌روزرسانی</h2>
''' + code('''
pip install --no-index --find-links dist --pre --upgrade agent-helper
python manage.py migrate
python manage.py check
''', 'bash')
    return page('deployment', 'استقرار', 'نصب روی سرور آفلاین، nginx، مدل خودمیزبان و نصب روی جدول‌های قدیمی', body)


def troubleshooting():
    rows = [
        ['همه‌ی پاسخ‌ها «امکان برقراری ارتباط… میسر نشد»', '<code>LLM_BASE_URL</code> تنظیم نشده یا سرور در دسترس نیست'],
        ['«خطایی در ارتباط با سرور هوش مصنوعی»', 'خطای HTTP از سرور مدل؛ <code>ModelCallLog.error</code> را ببینید (مثلاً 410 مدل منسوخ، 503 سهمیه)'],
        ['پاسخ LLM خالی یا JSON خراب', 'برخی دروازه‌ها بدون <code>stream: false</code> استریم می‌کنند؛ هسته آن را صریح می‌فرستد. مدل باید tool calling داشته باشد'],
        ['مسیر سریع هیچ‌وقت اجرا نمی‌شود', '<code>USE_FAST_ROUTER</code>، <code>JEV_BASE_URL</code>/<code>JEV_API_KEY</code>؛ <code>fast_reason</code> در لاگ دلیل را می‌گوید'],
        ['<code>agent_helper.E001</code> در check', 'ابزاری <code>proposes</code> دارد که ActionKind آن ثبت نشده'],
        ['ValueError «action kind … is not registered»', '<code>ctx.propose</code> با kind اشتباه یا افزونه‌ی اقدام نصب نیست'],
        ['کارت اقدام نمی‌آید', 'ابزار باید از <code>ctx.propose</code> استفاده کند (نه ساخت مستقیم PendingAction)'],
        ['تایید ۴۰۰ «منقضی شده»', 'مهلت گذشته؛ <code>expires_minutes</code> یا <code>ACTION_EXPIRES_MINUTES</code>'],
        ['استریم یک‌جا می‌رسد', 'بافر پروکسی؛ <code>proxy_buffering off</code>'],
        ['مدل مقدار حدس می‌زند', 'مدل ضعیف؛ قاعده‌ی پرامپت دامنه را صریح‌تر کنید و اعتبارسنجی را در ابزار نگه دارید (کارت تایید آخرین سد است)'],
        ['مدل ابزار لازم را ندارد', '<code>TOOL_SELECTION=\'all\'</code> یا برچسب‌ها/<code>intent_tags</code> را اصلاح کنید؛ <code>ModelCallLog.detail.offered</code>'],
        ['۴۲۹ از chat', 'سقف نرخ کاربر؛ <code>PER_MINUTE_LIMIT</code> و <code>DAILY_LIMIT</code>'],
    ]
    body = table(['علامت', 'علت و راه‌حل'], rows) + '''
<h2>پرسش‌های پرتکرار</h2>
<h3>آیا بدون مسیر سریع هم کار می‌کند؟</h3><p>بله؛ همه‌ی پیام‌ها به LLM می‌روند. مسیر سریع فقط بهینه‌سازی است.</p>
<h3>آیا می‌شود مدل را برای هر پیام عوض کرد؟</h3><p><code>run_assistant_agent(..., provider=...)</code> ارائه‌دهنده‌ی دلخواه می‌گیرد؛ view پیش‌فرض از تنظیمات می‌خواند.</p>
<h3>فارسی اجباری است؟</h3><p>قواعد هسته فارسی‌اند؛ با جایگزینی کلیدهای <code>identity</code> و <code>rule.*</code> می‌توانید زبان را عوض کنید. تاریخ‌ها شمسی (django-jalali) هستند.</p>
<h3>تاریخچه‌ی گفتگو چقدر به مدل داده می‌شود؟</h3><p>همه‌ی پیام‌های user و assistant همان گفتگو؛ خروجی ابزارهای نوبت‌های قبل ذخیره نمی‌شود، پس مدل در صورت نیاز دوباره ابزار را صدا می‌زند.</p>
<h3>برای محیط عملیاتی آماده است؟</h3><p>هنوز نه؛ این نسخه بتا است (<code>0.1.0b1</code>). سناریوها کامل تست شده‌اند ولی تا 1.0 ممکن است API تغییر کند؛ نسخه را دقیق pin کنید.</p>
'''
    return page('troubleshooting', 'عیب‌یابی و پرسش‌ها', 'خطاهای رایج و راه‌حل', body)


def changelog():
    body = '''
<h2>0.1.0b1 — بتا</h2>
<ul><li>نخستین پیش‌انتشار بتا؛ هنوز نسخه‌ی پایدار نیست و تا 1.0 ممکن است API و تنظیمات تغییر کنند.</li>
<li>مستندات به دو زبان فارسی و انگلیسی، همراه wheel.</li>
<li>رشته‌ی نسخه طبق PEP 440 (<code>agent_helper.__version__</code>)؛ نصب با <code>--pre</code> یا نسخه‌ی دقیق.</li></ul>
<h2>0.1.0 (داخلی)</h2>
<ul><li>نخستین نسخه‌ی جنریک.</li>
<li>قرارداد افزونه: <code>ToolSpec</code>، <code>ActionKind</code>، <code>CatalogProvider</code>، <code>PromptFragment</code>، <code>FastRoute</code>، <code>Plugin</code>.</li>
<li>اقدام معلق جنریک: پیش‌نمایش از <code>ActionKind.preview</code>، ذخیره‌ی وضعیت در هسته، ممیزی خطای اجرا.</li>
<li>مسیر سریع جنریک با سؤال‌های Jev از افزونه‌ها؛ backend مدل لوکال.</li>
<li>انتخاب ابزار و قاعده‌های مرتبط با پیام (<code>TOOL_SELECTION</code>).</li>
<li>تنظیمات <code>AGENT_HELPER</code> با پشتیبانی متغیرهای محیطی؛ بدون نشانی پیش‌فرض اینترنتی.</li>
<li>افزونه‌ی نمونه‌ی <code>agent-helper-demo</code> و پروژه‌ی مستقل.</li></ul>
'''
    return page('changelog', 'تغییرات', 'تاریخچه‌ی نسخه‌ها', body)

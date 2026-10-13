"""Core models: conversations, messages, pending actions, audit and request/model/tool logs.

A project that already has these tables under another app label can install the app with that label
(see the deployment docs).
"""
import jdatetime
from django.conf import settings
from django.db import models
from django_jalali.db import models as jmodels


class AssistantConversation(models.Model):
    """نشست گفتگوی کاربر با دستیار"""
    class Meta:
        verbose_name = 'گفتگوی دستیار'
        verbose_name_plural = 'گفتگوهای دستیار'
        ordering = ['-id']

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assistant_conversations', verbose_name='کاربر')
    title = models.CharField(max_length=255, default='گفتگوی جدید', verbose_name='عنوان')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    mode = models.CharField(max_length=20, blank=True, default='', verbose_name='حالت گفتگو',
                            help_text='حالت گفتگوی چندمرحله‌ای (مثلاً پر کردن فرم)؛ تا خالی نشود پیام‌ها به مسیر سریع نمی‌روند')

    def __str__(self):
        return f'{self.title} ({self.user.get_full_name()})'


class AssistantMessage(models.Model):
    """پیام‌های رد و بدل شده در گفتگوی دستیار"""
    ROLE_CHOICES = [
        ('user', 'کاربر'),
        ('assistant', 'دستیار'),
        ('system', 'سیستم'),
        ('tool', 'ابزار'),
    ]

    class Meta:
        verbose_name = 'پیام دستیار'
        verbose_name_plural = 'پیام‌های دستیار'
        ordering = ['id']

    conversation = models.ForeignKey(to=AssistantConversation, on_delete=models.CASCADE, related_name='messages', verbose_name='گفتگو')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='نقش')
    content = models.JSONField(default=dict, verbose_name='محتوا')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')

    def __str__(self):
        return f'{self.role}: {str(self.content)[:40]}'


class PendingAction(models.Model):
    """اقدام معلق نیازمند تایید صریح کاربر در رابط کاربری"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('confirmed', 'تأیید شده'),
        ('partial', 'تأیید جزئی'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
        ('expired', 'منقضی شده'),
    ]

    class Meta:
        verbose_name = 'اقدام معلق'
        verbose_name_plural = 'اقدامات معلق'
        ordering = ['-id']

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pending_actions', verbose_name='کاربر')
    conversation = models.ForeignKey(to=AssistantConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_actions', verbose_name='گفتگو')
    kind = models.CharField(max_length=50, default='approval', verbose_name='نوع اقدام')
    payload = models.JSONField(default=dict, verbose_name='داده‌های اقدام')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')
    expires_at = jmodels.jDateTimeField(verbose_name='زمان انقضا')
    executed_at = jmodels.jDateTimeField(null=True, blank=True, verbose_name='زمان اجرا')
    result = models.JSONField(null=True, blank=True, verbose_name='نتیجه')

    def __str__(self):
        return f'Action {self.id} ({self.kind}) - {self.status}'

    @property
    def is_expired(self):
        if self.status != 'pending':
            return False
        return jdatetime.datetime.now() > self.expires_at


class ActionAuditLog(models.Model):
    """لاگ حسابرسی اقدام‌های اجراشده

    node_id / flow_id / amount: شناسه‌ی مورد، شناسه‌ی شیء والد و مبلغ (همه اختیاری، به انتخاب افزونه).
    """
    class Meta:
        verbose_name = 'لاگ حسابرسی اقدام'
        verbose_name_plural = 'لاگ‌های حسابرسی اقدامات'
        ordering = ['-id']

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='action_audit_logs', verbose_name='کاربر اقدام‌کننده')
    action = models.ForeignKey(to=PendingAction, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', verbose_name='اقدام مربوطه')
    node_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='شناسه مورد')
    flow_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='شناسه شیء والد')
    amount = models.BigIntegerField(null=True, blank=True, verbose_name='مبلغ')
    status = models.CharField(max_length=30, verbose_name='وضعیت')
    detail = models.TextField(null=True, blank=True, verbose_name='توضیحات')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان ثبت')

    def __str__(self):
        return f'Log {self.id} - Node {self.node_id} ({self.status})'


class AssistantRequestLog(models.Model):
    """یک ردیف به‌ازای هر پیام کاربر: کدام مسیر، چند بار مدل و ابزار صدا زده شد، و چقدر طول کشید"""
    PATH_CHOICES = [('fast', 'مسیر سریع (بدون LLM)'), ('llm', 'LLM'), ('error', 'خطا')]
    STATUS_CHOICES = [('ok', 'موفق'), ('error', 'خطا')]

    class Meta:
        verbose_name = 'لاگ درخواست دستیار'
        verbose_name_plural = 'لاگ درخواست‌های دستیار'
        ordering = ['-id']
        indexes = [models.Index(fields=['-id', 'path'])]

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name='کاربر')
    conversation = models.ForeignKey(to=AssistantConversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='request_logs', verbose_name='گفتگو')
    message = models.TextField(blank=True, verbose_name='پیام کاربر (کوتاه‌شده)')
    path = models.CharField(max_length=5, choices=PATH_CHOICES, default='llm', verbose_name='مسیر پاسخ')
    fast_reason = models.CharField(max_length=60, blank=True, verbose_name='دلیل نرفتن به مسیر سریع')
    intent = models.CharField(max_length=20, blank=True, verbose_name='نیت تشخیص‌داده‌شده')
    intent_confidence = models.FloatField(null=True, blank=True, verbose_name='confidence نیت')
    status = models.CharField(max_length=5, choices=STATUS_CHOICES, default='ok', verbose_name='وضعیت')
    error = models.TextField(blank=True, verbose_name='خطا')
    intent_calls = models.PositiveSmallIntegerField(default=0, verbose_name='تعداد فراخوانی مدل تشخیص نیت')
    llm_calls = models.PositiveSmallIntegerField(default=0, verbose_name='تعداد فراخوانی LLM')
    tool_calls = models.PositiveSmallIntegerField(default=0, verbose_name='تعداد فراخوانی ابزار')
    input_tokens = models.PositiveIntegerField(default=0, verbose_name='توکن ورودی')
    output_tokens = models.PositiveIntegerField(default=0, verbose_name='توکن خروجی')
    duration_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name='مدت (میلی‌ثانیه)')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان')

    def __str__(self):
        return f'#{self.id} {self.path} {self.message[:30]}'


class ModelCallLog(models.Model):
    """هر بار که یک مدل (تشخیص نیت یا LLM) صدا زده شد"""
    KIND_CHOICES = [('intent', 'تشخیص نیت'), ('chat', 'LLM گفتگو')]

    class Meta:
        verbose_name = 'لاگ فراخوانی مدل'
        verbose_name_plural = 'لاگ فراخوانی مدل‌ها'
        ordering = ['-id']

    request = models.ForeignKey(to=AssistantRequestLog, on_delete=models.CASCADE, related_name='model_calls', verbose_name='درخواست')
    kind = models.CharField(max_length=6, choices=KIND_CHOICES, verbose_name='نوع')
    backend = models.CharField(max_length=30, verbose_name='backend')
    model = models.CharField(max_length=80, blank=True, verbose_name='مدل')
    ok = models.BooleanField(default=True, verbose_name='موفق')
    error = models.TextField(blank=True, verbose_name='خطا')
    attempts = models.PositiveSmallIntegerField(default=1, verbose_name='تعداد تلاش')
    input_tokens = models.PositiveIntegerField(default=0, verbose_name='توکن ورودی')
    output_tokens = models.PositiveIntegerField(default=0, verbose_name='توکن خروجی')
    duration_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name='مدت (میلی‌ثانیه)')
    detail = models.JSONField(default=dict, blank=True, verbose_name='جزئیات (پاسخ‌ها و confidence یا نام ابزارهای صدا زده‌شده)')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان')

    def __str__(self):
        return f'{self.kind} {self.backend} {self.model}'


class ToolCallLog(models.Model):
    """هر بار که یک ابزار دستیار اجرا شد"""
    class Meta:
        verbose_name = 'لاگ فراخوانی ابزار'
        verbose_name_plural = 'لاگ فراخوانی ابزارها'
        ordering = ['-id']

    request = models.ForeignKey(to=AssistantRequestLog, on_delete=models.CASCADE, related_name='tool_logs', verbose_name='درخواست')
    name = models.CharField(max_length=60, verbose_name='ابزار')
    arguments = models.JSONField(default=dict, blank=True, verbose_name='آرگومان‌ها')
    ok = models.BooleanField(default=True, verbose_name='موفق')
    result_summary = models.CharField(max_length=300, blank=True, verbose_name='خلاصه‌ی نتیجه')
    duration_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name='مدت (میلی‌ثانیه)')
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name='زمان')

    def __str__(self):
        return self.name


# generic aliases
Conversation = AssistantConversation
Message = AssistantMessage
RequestLog = AssistantRequestLog

"""Read-only admin for conversations, pending actions, audit and logs.

Base classes come from settings (AGENT_HELPER['ADMIN_BASE'] / ['ADMIN_INLINE_BASE']) so a project can use its
own admin theme; set AGENT_HELPER['REGISTER_ADMIN'] = False to register nothing.
"""
from django.contrib import admin, messages
from django.db.models import Avg, Count, Q, Sum
from django.utils.module_loading import import_string

from agent_helper import conf
from agent_helper.models import (
    ActionAuditLog, AssistantConversation, AssistantMessage, AssistantRequestLog, ModelCallLog, PendingAction, ToolCallLog,
)

ModelAdmin = import_string(conf.get('ADMIN_BASE'))
TabularInline = import_string(conf.get('ADMIN_INLINE_BASE'))


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ModelCallInline(ReadOnlyMixin, TabularInline):
    model = ModelCallLog
    extra = 0
    can_delete = False
    fields = ['kind', 'backend', 'model', 'ok', 'attempts', 'duration_ms', 'input_tokens', 'output_tokens', 'detail', 'error']
    readonly_fields = fields


class ToolCallInline(ReadOnlyMixin, TabularInline):
    model = ToolCallLog
    extra = 0
    can_delete = False
    fields = ['name', 'ok', 'duration_ms', 'result_summary', 'arguments']
    readonly_fields = fields


class AssistantRequestLogAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'created_at', 'user', 'short_message', 'path', 'fast_reason', 'intent', 'intent_calls', 'llm_calls',
                    'tool_calls', 'input_tokens', 'output_tokens', 'duration_ms', 'status']
    list_filter = ['path', 'status', 'fast_reason', 'intent', 'created_at']
    search_fields = ['message', 'user__username', 'user__first_name', 'user__last_name']
    autocomplete_fields = []
    readonly_fields = [f.name for f in AssistantRequestLog._meta.fields]
    inlines = [ModelCallInline, ToolCallInline]
    date_hierarchy = None

    @admin.display(description='پیام')
    def short_message(self, obj):
        return obj.message[:50]

    def changelist_view(self, request, extra_context=None):
        # خلاصه‌ی نتیجه‌ی فیلترهای فعلی: سهم مسیر سریع، میانگین مدت، مجموع توکن
        response = super().changelist_view(request, extra_context)
        try:
            qs = response.context_data['cl'].queryset
            total = qs.count()
            agg = qs.aggregate(fast=Count('id', filter=Q(path='fast')), avg_ms=Avg('duration_ms'), tin=Sum('input_tokens'), tout=Sum('output_tokens'),
                               avg_fast=Avg('duration_ms', filter=Q(path='fast')), avg_llm=Avg('duration_ms', filter=Q(path='llm')))
            if total:
                self.message_user(
                    request,
                    f"{total} درخواست | مسیر سریع: {agg['fast'] * 100 // total}٪ | میانگین مدت سریع: {int(agg['avg_fast'] or 0)}ms، LLM: {int(agg['avg_llm'] or 0)}ms "
                    f"| توکن ورودی/خروجی: {agg['tin'] or 0}/{agg['tout'] or 0}", messages.INFO)
        except Exception:
            pass
        return response


class ModelCallLogAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'created_at', 'kind', 'backend', 'model', 'ok', 'attempts', 'duration_ms', 'input_tokens', 'output_tokens']
    list_filter = ['kind', 'backend', 'ok', 'created_at']
    search_fields = ['model', 'error']
    readonly_fields = [f.name for f in ModelCallLog._meta.fields]


class ToolCallLogAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'created_at', 'name', 'ok', 'duration_ms', 'result_summary']
    list_filter = ['name', 'ok', 'created_at']
    search_fields = ['result_summary']
    readonly_fields = [f.name for f in ToolCallLog._meta.fields]


class ActionAuditLogAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'created_at', 'user', 'node_id', 'flow_id', 'amount', 'status', 'detail']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'detail']
    readonly_fields = [f.name for f in ActionAuditLog._meta.fields]


class PendingActionAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'created_at', 'user', 'kind', 'status', 'expires_at', 'executed_at']
    list_filter = ['status', 'kind', 'created_at']
    search_fields = ['user__username']
    readonly_fields = [f.name for f in PendingAction._meta.fields]


class AssistantMessageInline(ReadOnlyMixin, TabularInline):
    model = AssistantMessage
    extra = 0
    can_delete = False
    fields = ['role', 'content', 'created_at']
    readonly_fields = fields


class AssistantConversationAdmin(ReadOnlyMixin, ModelAdmin):
    list_display = ['id', 'title', 'user', 'created_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['user', 'title', 'created_at']
    inlines = [AssistantMessageInline]


if conf.flag('REGISTER_ADMIN'):
    admin.site.register(AssistantRequestLog, AssistantRequestLogAdmin)
    admin.site.register(ModelCallLog, ModelCallLogAdmin)
    admin.site.register(ToolCallLog, ToolCallLogAdmin)
    admin.site.register(ActionAuditLog, ActionAuditLogAdmin)
    admin.site.register(PendingAction, PendingActionAdmin)
    admin.site.register(AssistantConversation, AssistantConversationAdmin)

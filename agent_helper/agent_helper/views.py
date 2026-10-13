import json
import logging
import jdatetime
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer

from agent_helper import actions, conf
from agent_helper.models import AssistantConversation
from agent_helper.serializers import (
    ChatRequestSerializer,
    AssistantConversationSerializer,
    AssistantConversationDetailSerializer,
    PendingActionSerializer,
)
from agent_helper.llm import run_assistant_agent

logger = logging.getLogger(__name__)


def _fa(n) -> str:
    return str(n).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


def check_rate_limits(user):
    """
    بررسی محدودیت‌های درخواست در دقیقه (PER_MINUTE_LIMIT، پیش‌فرض ۳۰) و سقف روزانه (ASSISTANT_DAILY_LIMIT، پیش‌فرض ۱۰۰)
    در صورت عبور از سقف، پیام خطای فارسی برمی‌گرداند؛ در غیر این صورت None.
    """
    # ۱. محدودیت دقیقه‌ای
    per_minute = int(conf.get('PER_MINUTE_LIMIT'))
    minute_key = f"asst_rate_{user.id}"
    req_in_minute = cache.get(minute_key, 0)
    if req_in_minute >= per_minute:
        return f"تعداد درخواست‌های ارسالی شما بیش از حد مجاز در دقیقه ({_fa(per_minute)} درخواست) است. لطفاً چند لحظه صبر کنید و مجدداً تلاش نمایید."

    # ۲. سقف روزانه کاربر
    daily_limit = conf.daily_limit()
    today_str = jdatetime.date.today().strftime('%Y%m%d')
    daily_key = f"asst_daily_{user.id}_{today_str}"
    req_in_day = cache.get(daily_key, 0)
    if req_in_day >= daily_limit:
        return f"سقف مجاز روزانه شما برای استفاده از دستیار ({daily_limit} درخواست) به پایان رسیده است. لطفاً فردا مجدداً تلاش نمایید."

    # افزایش شمارنده‌ها
    if req_in_minute == 0:
        cache.set(minute_key, 1, timeout=60)
    else:
        try:
            cache.incr(minute_key)
        except Exception:
            cache.set(minute_key, req_in_minute + 1, timeout=60)

    if req_in_day == 0:
        cache.set(daily_key, 1, timeout=86400)
    else:
        try:
            cache.incr(daily_key)
        except Exception:
            cache.set(daily_key, req_in_day + 1, timeout=86400)

    return None


def stream_rate_limit_error(msg):
    def error_gen():
        yield f"data: {json.dumps({'event': 'error', 'message': msg}, ensure_ascii=False)}\n\n"
    res = StreamingHttpResponse(error_gen(), content_type='text/event-stream', status=status.HTTP_429_TOO_MANY_REQUESTS)
    res['Cache-Control'] = 'no-cache'
    res['X-Accel-Buffering'] = 'no'
    return res


class EventStreamRenderer(BaseRenderer):
    """رندرر اختصاصی برای ارسال رویدادهای Server-Sent Events (SSE)"""
    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ChatStreamView(APIView):
    """
    ارسال پیام به دستیار و دریافت پاسخ به‌صورت استریم SSE
    رویدادها: token, tool_status, pending_action, done, error
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [EventStreamRenderer]

    def post(self, request):
        user = request.user

        # بررسی ریت لیمیت و سقف مصرف روزانه
        limit_error = check_rate_limits(user)
        if limit_error:
            return stream_rate_limit_error(limit_error)

        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user_message = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')
        attachment = None
        if serializer.validated_data.get('image'):
            from agent_helper import vision
            try:
                attachment = vision.save_upload(user, serializer.validated_data['image'])
            except ValueError as e:
                return stream_rate_limit_error(str(e))

        # بازیابی یا ایجاد نشست گفتگو
        if conversation_id:
            conversation = get_object_or_404(
                AssistantConversation,
                id=conversation_id,
                user=user
            )
        else:
            # ایجاد عنوان گفتگو از ابتدای متن کاربر
            short_title = user_message.strip()[:40]
            if len(user_message.strip()) > 40:
                short_title += '...'
            conversation = AssistantConversation.objects.create(
                user=user,
                title=short_title or 'گفتگوی جدید'
            )

        # مولد استریم رویدادهای SSE
        def event_stream():
            try:
                for event in run_assistant_agent(
                    user=user,
                    conversation=conversation,
                    user_prompt=user_message,
                    attachment=attachment,
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.exception("Error in chat event stream: %s", str(e))
                err_payload = {
                    'event': 'error',
                    'message': 'خطایی در تولید پاسخ رخ داد.'
                }
                yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class ConversationListView(generics.ListAPIView):
    """فهرست نشست‌های گفتگوی خود کاربر لاگین‌شده"""
    serializer_class = AssistantConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AssistantConversation.objects.filter(
            user=self.request.user
        ).order_by('-id')


class ConversationDetailView(generics.RetrieveAPIView):
    """جزئیات یک نشست گفتگو و پیام‌های آن (فقط متعلق به کاربر جاری)"""
    serializer_class = AssistantConversationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AssistantConversation.objects.filter(
            user=self.request.user
        )


class ActionConfirmView(APIView):
    """
    تایید صریح اقدام معلق توسط کاربر لاگین‌شده؛ مستقل از مدل، با بررسی مجدد شروط و قفل atomic.
    بدنه‌ی درخواست (مثلاً node_ids و unchecked برای تایید گروهی) به ActionKind همان اقدام داده می‌شود.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        data = request.data if isinstance(request.data, dict) else {}
        res = actions.confirm_pending_action(user=request.user, action_id=action_id, params=data)
        status_code = res.pop('status_code', 200)
        return Response(data=res, status=status_code)


class ActionCancelView(APIView):
    """لغو اقدام معلق توسط کاربر لاگین‌شده"""
    permission_classes = [IsAuthenticated]

    def post(self, request, action_id):
        res = actions.cancel_pending_action(
            user=request.user,
            action_id=action_id
        )
        status_code = res.pop('status_code', 200)
        return Response(data=res, status=status_code)

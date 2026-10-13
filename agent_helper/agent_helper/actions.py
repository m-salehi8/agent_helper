"""Pending actions: the only way anything is executed.

Tools (and fast routes) may only *propose*: they create a ``PendingAction`` of a registered ``ActionKind``.
Execution happens only here, when the user presses the button: inside a transaction, with the action row locked,
after ownership, status and expiry checks; a second confirm returns the stored result (idempotent).
"""
from typing import Any, Dict, Optional

import jdatetime
from django.db import transaction

from agent_helper import conf
from agent_helper.models import ActionAuditLog, AssistantConversation, PendingAction
from agent_helper.registry import registry

_FA = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
FINAL_STATUSES = ('confirmed', 'partial', 'failed', 'cancelled')


def _minutes(kind) -> int:
    return int(kind.expires_minutes if kind and kind.expires_minutes else conf.get('ACTION_EXPIRES_MINUTES'))


def create_pending(user, conversation, kind: str, payload: Dict[str, Any], minutes: Optional[int] = None) -> PendingAction:
    """Store a proposal for ``user``. Nothing is executed."""
    spec = registry.action(kind)
    if spec is None:
        raise ValueError(f'action kind {kind!r} is not registered')
    required = (spec.propose_schema or {}).get('required') or []
    missing = [k for k in required if k not in (payload or {})]
    if missing:
        raise ValueError(f'action {kind}: payload is missing {missing}')
    expires_at = jdatetime.datetime.now() + jdatetime.timedelta(minutes=minutes or _minutes(spec))
    return PendingAction.objects.create(user=user, conversation=conversation, kind=kind, payload=payload,
                                        status='pending', expires_at=expires_at)


def pending_event(action: PendingAction) -> Dict[str, Any]:
    """``pending_action`` SSE event of a proposal: the ActionKind preview plus id and expiry"""
    spec = registry.action(action.kind)
    event = {'event': 'pending_action', 'action_id': action.id}
    event.update(spec.preview(action.payload) if spec else {})
    event['expires_at'] = action.expires_at.strftime('%Y/%m/%d %H:%M')
    return event


def audit(user, action, status: str, detail: str = '', **refs) -> ActionAuditLog:
    """Audit row for an executed (or failed) item; ``refs``: node_id, flow_id, amount"""
    return ActionAuditLog.objects.create(user=user, action=action, status=status, detail=(detail or '')[:2000], **refs)


def confirm_pending_action(user, action_id: int, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a pending action for its owner. ``params`` is the confirm request body (passed to the ActionKind).

    Returns a dict with ``status_code`` (HTTP status for the view)."""
    params = params if params is not None and hasattr(params, 'get') else {}
    with transaction.atomic():
        action = PendingAction.objects.select_for_update().filter(id=action_id).first()
        if not action:
            return {'error': 'اقدام مورد نظر یافت نشد.', 'status_code': 404}

        if action.user != user:
            return {'error': 'شما مجاز به تأیید این اقدام نیستید.', 'status_code': 403}

        # idempotent
        if action.status in ('confirmed', 'partial'):
            return {
                'message': 'این اقدام قبلاً اجرا شده است.',
                'already_confirmed': True,
                'status': action.status,
                'action_id': action.id,
                'results': action.result or [],
                'status_code': 200
            }

        if action.status != 'pending':
            return {
                'error': f'این اقدام در وضعیت «{action.get_status_display()}» است و قابل تأیید نیست.',
                'status_code': 400
            }

        spec = registry.action(action.kind)
        if action.is_expired:
            action.status = 'expired'
            action.save(update_fields=['status'])
            minutes = str(_minutes(spec)).translate(_FA)
            return {'error': f'مهلت زمانی تایید این اقدام ({minutes} دقیقه) منقضی شده است.', 'status_code': 400}

        if spec is None:
            return {'error': f'نوع اقدام «{action.kind}» پشتیبانی نمی‌شود.', 'status_code': 400}

        try:
            with transaction.atomic():  # savepoint: a crashing executor leaves no partial change
                res = spec.execute(user, action, params)
        except Exception as e:  # noqa: BLE001 - recorded as a failed action, never a half-done one
            label = spec.audit_label or spec.kind
            audit(user, action, 'failed', f'{label}: {type(e).__name__}: {e}')
            res = {'error': 'اجرای این اقدام با خطا مواجه شد.', 'status': 'failed', 'action_id': action.id,
                   'results': [{'status': 'failed', 'detail': f'{type(e).__name__}: {e}'[:300]}], 'status_code': 500}

        # فقط نتیجه‌ی نهایی وضعیت اقدام را عوض می‌کند؛ خطای اعتبارسنجی پارامترها (بدون status) اقدام را pending نگه می‌دارد
        if res.get('status') in FINAL_STATUSES:
            action.status = res['status']
            action.executed_at = jdatetime.datetime.now()
            action.result = res.get('results') or []
            action.save()
            if spec.resets_mode and action.conversation_id and res['status'] == 'confirmed':
                AssistantConversation.objects.filter(id=action.conversation_id).update(mode='')
        return res


def cancel_pending_action(user, action_id: int) -> Dict[str, Any]:
    """لغو اقدام معلق توسط کاربر"""
    with transaction.atomic():
        action = PendingAction.objects.select_for_update().filter(id=action_id).first()
        if not action:
            return {'error': 'اقدام مورد نظر یافت نشد.', 'status_code': 404}
        if action.user != user:
            return {'error': 'شما مجاز به لغو این اقدام نیستید.', 'status_code': 403}
        if action.status != 'pending':
            return {'error': f'این اقدام در وضعیت «{action.get_status_display()}» است و قابل لغو نیست.', 'status_code': 400}

        action.status = 'cancelled'
        action.save(update_fields=['status'])
        return {'message': 'اقدام با موفقیت لغو شد.', 'status': 'cancelled', 'action_id': action.id, 'status_code': 200}

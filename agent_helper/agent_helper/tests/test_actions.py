"""Generic pending actions: proposals only through registered ActionKinds, execution only on confirm."""
import jdatetime
from django.test import TestCase

from agent_helper import actions
from agent_helper.models import ActionAuditLog, AssistantConversation, PendingAction
from agent_helper.plugins import ActionKind, Plugin
from agent_helper.registry import override
from agent_helper.testing import make_user

CALLS = []


def _execute(user, action, params):
    CALLS.append((user.pk, action.pk, dict(params)))
    if params.get('bad'):
        return {'error': 'پارامتر نامعتبر', 'status_code': 400}
    if params.get('crash'):
        raise RuntimeError('boom')
    actions.audit(user, action, 'confirmed', 'ok', node_id=1)
    return {'status': 'confirmed', 'message': 'انجام شد', 'results': [{'status': 'success'}], 'status_code': 200}


KIND = ActionKind(kind='demo_note', execute=_execute, preview=lambda p: {'kind': 'demo_note', 'text': p['text']},
                  propose_schema={'type': 'object', 'required': ['text']}, audit_label='یادداشت', resets_mode=True)


class PendingActionTests(TestCase):
    def setUp(self):
        CALLS.clear()
        self.user = make_user('ah_owner')
        self.other = make_user('ah_other')
        self._override = override([Plugin(name='t', actions=[KIND])])
        self._override.__enter__()

    def tearDown(self):
        self._override.__exit__(None, None, None)

    def _propose(self, **payload):
        conv = AssistantConversation.objects.create(user=self.user, title='t', mode='create')
        return actions.create_pending(self.user, conv, 'demo_note', {'text': 'سلام', **payload})

    def test_propose_validates_kind_and_payload_and_builds_preview(self):
        with self.assertRaises(ValueError):
            actions.create_pending(self.user, None, 'unknown', {})
        with self.assertRaises(ValueError):
            actions.create_pending(self.user, None, 'demo_note', {})  # required key missing
        action = self._propose()
        self.assertEqual(action.status, 'pending')
        event = actions.pending_event(action)
        self.assertEqual((event['event'], event['action_id'], event['text']), ('pending_action', action.id, 'سلام'))
        self.assertEqual(CALLS, [])  # nothing executed by proposing

    def test_confirm_lifecycle(self):
        action = self._propose()
        self.assertEqual(actions.confirm_pending_action(self.other, action.id)['status_code'], 403)
        bad = actions.confirm_pending_action(self.user, action.id, {'bad': True})
        self.assertEqual(bad['status_code'], 400)
        action.refresh_from_db()
        self.assertEqual(action.status, 'pending')  # a rejected request keeps the action pending
        ok = actions.confirm_pending_action(self.user, action.id, {'x': 1})
        self.assertEqual(ok['status'], 'confirmed')
        action.refresh_from_db()
        self.assertEqual((action.status, action.result), ('confirmed', [{'status': 'success'}]))
        self.assertIsNotNone(action.executed_at)
        self.assertEqual(action.conversation.mode, '')  # resets_mode
        again = actions.confirm_pending_action(self.user, action.id)
        self.assertTrue(again['already_confirmed'])
        self.assertEqual(len([c for c in CALLS if not c[2].get('bad')]), 1)  # idempotent: executed once
        self.assertEqual(ActionAuditLog.objects.filter(action=action, status='confirmed').count(), 1)

    def test_expired_crash_cancel_and_unknown_kind(self):
        action = self._propose()
        PendingAction.objects.filter(id=action.id).update(expires_at=jdatetime.datetime.now() - jdatetime.timedelta(minutes=1))
        self.assertIn('منقضی', actions.confirm_pending_action(self.user, action.id)['error'])
        self.assertEqual(PendingAction.objects.get(id=action.id).status, 'expired')

        action = self._propose()
        out = actions.confirm_pending_action(self.user, action.id, {'crash': True})
        self.assertEqual(out['status'], 'failed')
        self.assertEqual(PendingAction.objects.get(id=action.id).status, 'failed')
        self.assertTrue(ActionAuditLog.objects.filter(action=action, status='failed', detail__startswith='یادداشت').exists())

        action = self._propose()
        self.assertEqual(actions.cancel_pending_action(self.other, action.id)['status_code'], 403)
        self.assertEqual(actions.cancel_pending_action(self.user, action.id)['status'], 'cancelled')
        self.assertEqual(actions.confirm_pending_action(self.user, action.id)['status_code'], 400)

        orphan = PendingAction.objects.create(user=self.user, kind='gone', payload={},
                                              expires_at=jdatetime.datetime.now() + jdatetime.timedelta(minutes=5))
        self.assertEqual(actions.confirm_pending_action(self.user, orphan.id)['status_code'], 400)

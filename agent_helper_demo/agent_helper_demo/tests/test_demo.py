"""The core with only the demo plugin: agent loop, pending action, confirm endpoint, fast route.

Only the demo plugin is registered (registry.override), so nothing else a host project installs is involved.
"""
import jdatetime
import json
from unittest import mock

from django.apps import apps
from django.test import TestCase

if not apps.is_installed('agent_helper_demo'):
    import unittest
    raise unittest.SkipTest('agent_helper_demo is not installed (run with packages/agent_helper_demo/manage.py)')
from rest_framework.test import APIRequestFactory, force_authenticate

from agent_helper import router
from agent_helper.llm import LLMResponse, MockProvider, ToolCall, run_assistant_agent
from agent_helper.models import ActionAuditLog, AssistantConversation, AssistantRequestLog, PendingAction
from agent_helper.registry import override
from agent_helper.testing import fast_router, make_user
from agent_helper.views import ActionConfirmView, ChatStreamView
from agent_helper_demo.models import DemoNote
from agent_helper_demo.plugin import PLUGIN


class DemoPluginTests(TestCase):
    def setUp(self):
        self.user = make_user('demo_user')
        self.other = make_user('demo_other')
        self._override = override([PLUGIN])
        self._override.__enter__()

    def tearDown(self):
        self._override.__exit__(None, None, None)

    def test_only_the_demo_plugin_is_registered(self):
        from agent_helper.registry import registry
        self.assertEqual([t.name for t in registry.tools()], ['list_my_notes', 'get_leave_balance', 'propose_add_note'])
        self.assertEqual(registry.check(), [])

    def test_agent_loop_reads_and_proposes_but_never_saves(self):
        DemoNote.objects.create(user=self.user, text='خرید شیر')
        DemoNote.objects.create(user=self.other, text='یادداشت کاربر دیگر')
        conv = AssistantConversation.objects.create(user=self.user, title='t')
        provider = MockProvider([
            LLMResponse(tool_calls=[ToolCall(id='1', name='list_my_notes', arguments={'user_id': self.other.id})]),
            LLMResponse(tool_calls=[ToolCall(id='2', name='propose_add_note', arguments={'text': 'جلسه ساعت ۱۰'})]),
            LLMResponse(text='پیش‌نویس آماده است؛ دکمه را بزنید.'),
        ])
        with fast_router(on=False):
            events = list(run_assistant_agent(self.user, conv, 'یادداشت‌هایم را بگو و یکی هم اضافه کن', provider=provider))
        notes = next(e for e in events if e['event'] == 'note_list')['items']
        self.assertEqual([n['text'] for n in notes], ['خرید شیر'])  # only the request user's notes
        pending = next(e for e in events if e['event'] == 'pending_action')
        self.assertEqual((pending['kind'], pending['text']), ('add_note', 'جلسه ساعت ۱۰'))
        self.assertEqual(DemoNote.objects.filter(user=self.user).count(), 1)  # nothing saved yet
        self.assertEqual(events[-1]['event'], 'done')
        # the model saw only demo tools and no other plugin's prompt rule
        first = provider.call_history[0]
        self.assertEqual({t['name'] for t in first['tools']}, {'list_my_notes', 'get_leave_balance', 'propose_add_note'})
        self.assertIn('Prompt Injection', first['system'])
        log = AssistantRequestLog.objects.get(conversation=conv)
        self.assertEqual((log.llm_calls, log.tool_calls, log.path), (3, 2, 'llm'))

    def test_confirm_endpoint_saves_once(self):
        action = PendingAction.objects.create(user=self.user, kind='add_note', payload={'text': 'سلام'},
                                              expires_at=jdatetime.datetime.now() + jdatetime.timedelta(minutes=5))
        factory = APIRequestFactory()
        for who, code in ((self.other, 403), (self.user, 200), (self.user, 200)):
            req = factory.post(f'/api/assistant/actions/{action.id}/confirm/', {}, format='json')
            force_authenticate(req, user=who)
            self.assertEqual(ActionConfirmView.as_view()(req, action_id=action.id).status_code, code)
        self.assertEqual(DemoNote.objects.filter(user=self.user, text='سلام').count(), 1)
        self.assertEqual(PendingAction.objects.get(id=action.id).status, 'confirmed')
        self.assertEqual(ActionAuditLog.objects.filter(action=action, status='created').count(), 1)

    def test_fast_route_without_llm_or_classifier(self):
        with fast_router(), mock.patch('agent_helper.nlu.classify', side_effect=AssertionError('not called')):
            res = router.try_fast_path(self.user, None, 'چند روز مرخصی دارم؟')
        self.assertEqual(res['path'], 'fast')
        self.assertIn('۲۶', res['text'])

    def test_sse_view_streams_with_demo_plugin(self):
        factory = APIRequestFactory()
        req = factory.post('/api/assistant/chat/', {'message': 'سلام'}, format='json')
        force_authenticate(req, user=self.user)
        with fast_router(on=False), mock.patch('agent_helper.llm.get_llm_provider', return_value=MockProvider([LLMResponse(text='سلام!')])):
            resp = ChatStreamView.as_view()(req)
            body = b''.join(resp.streaming_content).decode()
        events = [json.loads(line[6:]) for line in body.split('\n\n') if line.startswith('data: ')]
        self.assertEqual([e['event'] for e in events], ['token', 'done'])

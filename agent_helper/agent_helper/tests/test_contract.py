"""Plugin contract and registry tests (no database, no network)."""
from django.test import SimpleTestCase

from agent_helper import registry as reg
from agent_helper import tools
from agent_helper.plugins import ActionKind, Plugin, ToolSpec


def _echo(user, args, ctx):
    return {'user': getattr(user, 'id', user), 'args': args, 'has_ctx': ctx is not None}


SCHEMA = {'type': 'object', 'properties': {}, 'required': []}


class ToolSpecContractTests(SimpleTestCase):
    def test_invalid_specs_are_rejected(self):
        with self.assertRaises(ValueError):
            ToolSpec(name='bad name', description='', json_schema=SCHEMA, handler=_echo)
        with self.assertRaises(ValueError):
            ToolSpec(name='t', description='', json_schema={'type': 'string'}, handler=_echo)
        with self.assertRaises(ValueError):  # a tool that is not read-only must say which action it proposes
            ToolSpec(name='t', description='', json_schema=SCHEMA, handler=_echo, read_only=False)

    def test_schemas_and_status(self):
        spec = ToolSpec(name='t', description='d', json_schema=SCHEMA, handler=_echo, status=lambda a: f'x{a.get("n")}')
        self.assertEqual(spec.anthropic_schema(), {'name': 't', 'description': 'd', 'input_schema': SCHEMA})
        self.assertEqual(spec.openai_schema()['function']['parameters'], SCHEMA)
        self.assertEqual(spec.status_text({'n': 2}), 'x2')
        self.assertIn('t', ToolSpec(name='t', description='', json_schema=SCHEMA, handler=_echo).status_text({}))


class RegistryTests(SimpleTestCase):
    def test_override_register_and_execute_with_given_user(self):
        spec = ToolSpec(name='echo', description='', json_schema=SCHEMA, handler=_echo)
        with reg.override([Plugin(name='p', tools=[spec])]):
            self.assertEqual([t.name for t in tools.specs()], ['echo'])
            out = tools.execute_tool('echo', {'user_id': 999}, user=type('U', (), {'id': 7})())
            self.assertEqual(out['user'], 7)  # the user comes from the caller, never from arguments
            self.assertIn('error', tools.execute_tool('missing', {}, user=None))
        self.assertIsNone(reg.registry.tool('echo'))  # override restored the real plugins

    def test_duplicate_names_and_unknown_proposed_kind(self):
        a = ToolSpec(name='dup', description='', json_schema=SCHEMA, handler=_echo)
        with reg.override([Plugin(name='p1', tools=[a])]) as r:
            with self.assertRaises(ValueError):
                r.register(Plugin(name='p2', tools=[a]))
            r.register(Plugin(name='p1', tools=[a]))  # re-registering the same plugin replaces it
            self.assertEqual(len(r.tools()), 1)
            proposer = ToolSpec(name='prop', description='', json_schema=SCHEMA, handler=_echo, read_only=False, proposes='nope')
            r.register(Plugin(name='p3', tools=[proposer]))
            self.assertTrue(any('nope' in e for e in r.check()))
            r.register(Plugin(name='p4', actions=[ActionKind(kind='nope', execute=lambda u, a, p: {})]))
            self.assertEqual(r.check(), [])

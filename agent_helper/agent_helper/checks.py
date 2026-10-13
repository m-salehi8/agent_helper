from django.core import checks


def check_registry(app_configs=None, **kwargs):
    """System check: every proposing tool names a registered ActionKind."""
    from agent_helper.registry import registry
    return [checks.Error(msg, id='agent_helper.E001') for msg in registry.check()]

from django.apps import AppConfig


class AgentHelperConfig(AppConfig):
    """Core app. A project that already has the tables under another label can subclass this config and set
    ``label`` (see the deployment docs)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent_helper'
    label = 'agent_helper'
    verbose_name = 'دستیار هوشمند'

    def ready(self):
        from django.core import checks
        from agent_helper.checks import check_registry
        checks.register(check_registry)

from django.apps import AppConfig


class AgentHelperDemoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agent_helper_demo'
    label = 'agent_helper_demo'
    verbose_name = 'دستیار هوشمند: افزونه‌ی نمونه'

    def ready(self):
        import agent_helper
        from agent_helper_demo.plugin import PLUGIN
        agent_helper.register(PLUGIN)

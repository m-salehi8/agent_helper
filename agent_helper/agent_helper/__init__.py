"""agent_helper: a generic, plugin-based chat agent for Django (LLM tool loop, no-LLM fast routes, pending
actions confirmed only by the user, request/model/tool logs, SSE)."""
__version__ = '0.1.0b1'


def register(plugin):
    """Register a :class:`agent_helper.plugins.Plugin` (call from ``AppConfig.ready()``)."""
    from agent_helper.registry import register as _register
    return _register(plugin)

"""Running registered tools.

Security invariant: a tool always runs for the authenticated ``user`` given by the caller (the view's
``request.user``); no user id is ever taken from model arguments.
"""
from typing import Any, Dict, Iterable, List, Optional

from agent_helper.plugins import ToolContext, ToolSpec
from agent_helper.registry import registry


def specs(names: Optional[Iterable[str]] = None) -> List[ToolSpec]:
    all_specs = registry.tools()
    if names is None:
        return all_specs
    wanted = set(names)
    return [s for s in all_specs if s.name in wanted]


def anthropic_schemas(selected: Optional[List[ToolSpec]] = None) -> List[Dict[str, Any]]:
    return [s.anthropic_schema() for s in (registry.tools() if selected is None else selected)]


def openai_schemas(selected: Optional[List[ToolSpec]] = None) -> List[Dict[str, Any]]:
    return [s.openai_schema() for s in (registry.tools() if selected is None else selected)]


def set_mode(conversation, mode: str):
    """Conversation dialog mode (e.g. 'create' while a multi-turn form is being filled); short follow-up answers
    in a non-empty mode do not go to the fast route."""
    if conversation is not None and getattr(conversation, 'mode', None) != mode:
        conversation.mode = mode
        conversation.save(update_fields=['mode'])


def execute_tool(name: str, arguments: Dict[str, Any], user, conversation=None, ctx: Optional[ToolContext] = None) -> Dict[str, Any]:
    """Run one tool for ``user`` and return its result dict (``{'error': ...}`` for unknown tools)."""
    spec = registry.tool(name)
    if spec is None:
        return {'error': f'ابزار «{name}» ناشناخته است.'}
    if spec.conversation_mode is not None:
        set_mode(conversation, spec.conversation_mode)
    if ctx is None:
        ctx = ToolContext(user=user, conversation=conversation)
    return spec.handler(user, arguments if isinstance(arguments, dict) else {}, ctx)


def run_logged(trace, name: str, args: Dict[str, Any], user, conversation=None, collect: Optional[list] = None) -> Dict[str, Any]:
    """execute_tool + tool log in the request trace; PendingActions proposed by the tool are appended to ``collect``."""
    ctx = ToolContext(user=user, conversation=conversation, trace=trace)
    if trace is None:
        result = execute_tool(name, args, user, conversation, ctx)
    else:
        result = trace.run_tool(name, args, lambda: execute_tool(name, args, user, conversation, ctx))
    if collect is not None:
        collect.extend(ctx.proposed)
    return result

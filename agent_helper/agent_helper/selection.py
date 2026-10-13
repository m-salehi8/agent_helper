"""Which tools (and tagged prompt rules) the LLM gets for one message.

Signals, all from the current message or conversation:
- the conversation's dialog mode (the route of the same name),
- an image attachment (plugins' ``attachment_tags``),
- regex guards of gate routes,
- the light classifier answers, if the fast route ran (yes/no gates and the main intent, p >= 0.5),
- tools already used in this conversation (follow-ups like "approve those" keep their tools).

No signal from the message itself ⇒ ``None`` = every tool (the previous behaviour). Untagged tools and prompt
fragments are always included.
"""
from typing import Iterable, List, Optional, Set

from agent_helper import conf
from agent_helper.plugins import ToolSpec
from agent_helper.registry import registry

SIGNAL_P = 0.5


def message_tags(conversation, text: str, attachment=None, cls: Optional[dict] = None) -> Set[str]:
    routes = registry.routes()
    tags: Set[str] = set()
    mode = getattr(conversation, 'mode', '') or ''
    for route in routes:
        if mode and route.name == mode:
            tags.update(route.tags)
        if route.guard is not None and route.guard(text or ''):
            tags.update(route.tags)
        if cls and route.gate_question and cls.get(route.gate_key, {}).get('p', 0) >= SIGNAL_P:
            tags.update(route.tags)
        intent = (cls or {}).get('intent')
        if intent and intent['confidence'] >= SIGNAL_P:
            tags.update(route.intent_tags.get(intent['choice'], ()))
    if attachment:
        tags.update(registry.attachment_tags())
    return tags


def history_tags(conversation) -> Set[str]:
    if conversation is None or getattr(conversation, 'pk', None) is None:
        return set()
    from agent_helper.models import ToolCallLog
    used = set(ToolCallLog.objects.filter(request__conversation=conversation).values_list('name', flat=True).distinct())
    return {t for spec in registry.tools() if spec.name in used for t in spec.tags}


def select_tags(conversation, text: str, attachment=None, cls: Optional[dict] = None) -> Optional[Set[str]]:
    """Selected tags, or None for everything"""
    if str(conf.get('TOOL_SELECTION')).lower() != 'auto':
        return None
    tags = message_tags(conversation, text, attachment, cls)
    if not tags:
        return None
    return tags | history_tags(conversation)


def select_tools(tags: Optional[Iterable[str]]) -> List[ToolSpec]:
    specs = registry.tools()
    if tags is None:
        return specs
    tags = set(tags)
    return [s for s in specs if not s.tags or set(s.tags) & tags]

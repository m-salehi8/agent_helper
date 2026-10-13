"""Stable plugin contract of agent_helper.

A plugin is a bundle of domain pieces that the generic core (agent loop, fast router, pending actions, logging)
uses without knowing the domain:

- ``ToolSpec``: a tool the LLM (or a fast route) may call. Tools only read data or *propose* a ``PendingAction``;
  there is no tool that executes a change. The acting user is always ``request.user``; it is never read from
  model output.
- ``ActionKind``: how a proposed ``PendingAction`` of one kind is previewed and executed. Execution happens only
  in the confirm endpoint, inside a transaction, with the action row locked.
- ``CatalogProvider``: entities the user may refer to by name (e.g. process types). Used for the Jev
  "which one?" question and for plain text matching.
- ``PromptFragment``: a piece of the system prompt (domain rules). The core keeps only the generic rules.
- ``FastRoute``: an optional no-LLM route (regex guard and/or Jev yes/no question, plus a handler).

Register a plugin from ``AppConfig.ready()``::

    import agent_helper
    agent_helper.register(Plugin(name='notes', tools=[...], actions=[...]))
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

JSON = Dict[str, Any]

_NAME_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


@dataclass
class ToolContext:
    """Per-call context passed to a tool handler.

    ``user`` is the authenticated request user (the same object passed as the handler's first argument).
    ``proposed`` collects the PendingActions created through :meth:`propose` during this call; the core turns
    each one into a ``pending_action`` SSE event.
    """
    user: Any = None
    conversation: Any = None
    trace: Any = None
    proposed: List[Any] = field(default_factory=list)

    def propose(self, kind: str, payload: JSON, minutes: Optional[int] = None):
        """Create a PendingAction of a registered ``ActionKind`` for ``self.user``; nothing is executed."""
        from agent_helper import actions
        action = actions.create_pending(self.user, self.conversation, kind, payload, minutes=minutes)
        self.proposed.append(action)
        return action


ToolHandler = Callable[[Any, JSON, ToolContext], JSON]


@dataclass(frozen=True)
class ToolSpec:
    """A tool exposed to the model.

    Args:
        name: unique tool name (``[A-Za-z0-9_-]``, max 64).
        description: text the model reads to decide when to call the tool.
        json_schema: JSON schema of the arguments (``type: object``).
        handler: ``handler(user, args, ctx) -> dict``; ``user`` is always ``request.user``.
        read_only: True for tools that only read. A tool that is not read-only must name the ``ActionKind`` it
            proposes in ``proposes`` and may only create PendingActions (via ``ctx.propose``).
        proposes: kind of the PendingAction this tool proposes (required when ``read_only`` is False).
        tags: topic labels used to give the model only the tools relevant to a message.
        status: text (or ``callable(args) -> text``) for the ``tool_status`` SSE event.
        events: ``callable(result) -> [event, ...]`` extra SSE events built from the tool result.
        conversation_mode: if not None, ``conversation.mode`` is set to this value before the call
            (a non-empty mode keeps short follow-up answers away from the fast route).
    """
    name: str
    description: str
    json_schema: JSON
    handler: ToolHandler
    read_only: bool = True
    proposes: Optional[str] = None
    tags: Tuple[str, ...] = ()
    status: Union[str, Callable[[JSON], str], None] = None
    events: Optional[Callable[[JSON], List[JSON]]] = None
    conversation_mode: Optional[str] = None

    def __post_init__(self):
        if not _NAME_RE.match(self.name or ''):
            raise ValueError(f'invalid tool name: {self.name!r}')
        if not callable(self.handler):
            raise ValueError(f'tool {self.name}: handler must be callable')
        if (self.json_schema or {}).get('type') != 'object':
            raise ValueError(f'tool {self.name}: json_schema must be an object schema')
        if not self.read_only and not self.proposes:
            raise ValueError(f'tool {self.name}: a non read-only tool must declare the ActionKind it proposes')

    def anthropic_schema(self) -> JSON:
        return {'name': self.name, 'description': self.description, 'input_schema': self.json_schema}

    def openai_schema(self) -> JSON:
        return {'type': 'function', 'function': {'name': self.name, 'description': self.description,
                                                 'parameters': self.json_schema}}

    def status_text(self, args: JSON) -> str:
        if callable(self.status):
            return self.status(args or {})
        return self.status or f'در حال اجرای ابزار {self.name}...'


@dataclass(frozen=True)
class ActionKind:
    """How PendingActions of one ``kind`` are previewed and executed.

    Args:
        kind: value stored in ``PendingAction.kind``.
        execute: ``execute(user, action, params) -> dict``. Called only by the confirm endpoint, inside
            ``transaction.atomic()`` with the action row locked, after ownership, status and expiry checks.
            ``params`` is the confirm request body (e.g. the subset of rows the user ticked).
            Return a dict with ``status`` in (confirmed, partial, failed, cancelled), ``message`` and ``results``
            to finish the action, or a dict with ``error`` and ``status_code`` (and no ``status``) to reject
            the request and leave the action pending.
        preview: ``preview(payload) -> dict`` fields of the ``pending_action`` SSE event (what the UI shows).
        propose_schema: optional JSON schema of the payload; its ``required`` keys are checked on propose.
        audit_label: short human label used in audit entries written by the core.
        expires_minutes: lifetime of a pending action of this kind.
        resets_mode: after a successful execution, clear ``conversation.mode``.
    """
    kind: str
    execute: Callable[[Any, Any, JSON], JSON]
    preview: Callable[[JSON], JSON] = field(default=lambda payload: {})
    propose_schema: Optional[JSON] = None
    audit_label: str = ''
    expires_minutes: int = 10
    resets_mode: bool = False

    def __post_init__(self):
        if not _NAME_RE.match(self.kind or ''):
            raise ValueError(f'invalid action kind: {self.kind!r}')
        if not callable(self.execute):
            raise ValueError(f'action {self.kind}: execute must be callable')


@dataclass(frozen=True)
class CatalogEntry:
    """One selectable entity (e.g. a process type). ``key`` is what the Jev question returns."""
    key: str
    title: str
    aliases: Tuple[str, ...] = ()
    description: str = ''
    data: Any = None


class CatalogProvider:
    """Entities the model or the fast router must choose between.

    Subclass and implement :meth:`entries`. ``question_key`` names the Jev choice question built from the
    entries; ``instructions`` is its instruction text.
    """
    name: str = 'catalog'
    question_key: str = 'catalog'
    instructions: str = 'Which item does the message refer to?'
    none_label: str = 'No specific item is mentioned'

    def entries(self) -> Sequence[CatalogEntry]:
        raise NotImplementedError


@dataclass(frozen=True)
class PromptFragment:
    """A piece of the system prompt.

    ``section='identity'`` fragments open the prompt; ``section='rule'`` fragments are numbered in ``order``.
    A fragment with the same ``key`` as an earlier one (e.g. a core rule) replaces it.
    Fragments with ``tags`` are left out when tool selection picked none of those tags.
    """
    text: str
    order: int = 100
    key: Optional[str] = None
    tags: Tuple[str, ...] = ()
    section: str = 'rule'


@dataclass
class RouteRequest:
    """Input of a fast route handler."""
    user: Any
    conversation: Any
    text: str
    cls: Optional[JSON]
    threshold: float
    gate_p: Dict[str, float]
    trace: Any = None

    def run_tool(self, name: str, args: JSON) -> JSON:
        """Run a registered tool for ``self.user`` (logged in the request trace); pending actions it proposes
        are added to the reply as ``pending_action`` events by :meth:`reply`."""
        from agent_helper import tools
        return tools.run_logged(self.trace, name, args, self.user, self.conversation, collect=self._proposed)

    def reply(self, text: str, events: Optional[List[JSON]] = None) -> JSON:
        from agent_helper import actions
        pending = [actions.pending_event(a) for a in self._proposed]
        self._proposed.clear()
        return {'text': text, 'events': (events or []) + pending + [{'event': 'token', 'text': text}], 'path': 'fast'}

    def __post_init__(self):
        self._proposed: List[Any] = []


@dataclass(frozen=True)
class Defer:
    """Route result: send the message to the LLM; ``reason`` is logged."""
    reason: str


RouteHandler = Callable[[RouteRequest], Union[JSON, Defer, None]]


@dataclass(frozen=True)
class FastRoute:
    """A no-LLM route.

    Gate routes have a ``guard`` (cheap regex) and/or a ``gate_question`` (Jev yes/no question, asked as
    ``is_<name>``). When the guard matches, or Jev answers yes with confidence >= threshold (and ``gate_veto``
    does not match), the route's ``handler`` runs; a gate route without handler sends the message to the LLM
    with reason ``<name>_request``.

    Main routes have neither guard nor gate question; they run after the gates, in ``order``, with the Jev
    answers (``questions`` are added to the Jev call and are also the questions of the local-LLM backend).
    A handler returns a reply dict (``RouteRequest.reply``), ``Defer(reason)``, or None to try the next route.

    ``tags`` are the tool/prompt tags this route stands for; ``intent_tags`` maps a choice of the ``intent``
    question to tags. Both feed tool selection when the message goes to the LLM.
    """
    name: str
    handler: Optional[RouteHandler] = None
    guard: Optional[Callable[[str], bool]] = None
    gate_question: Optional[JSON] = None
    gate_veto: Optional[Callable[[str], bool]] = None
    questions: Mapping[str, JSON] = field(default_factory=dict)
    tags: Tuple[str, ...] = ()
    intent_tags: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    order: int = 100

    @property
    def is_gate(self) -> bool:
        return self.guard is not None or self.gate_question is not None

    @property
    def gate_key(self) -> str:
        return f'is_{self.name}'


@dataclass
class Plugin:
    """Everything one plugin contributes. ``attachment_tags`` are selected when the message has an image."""
    name: str
    tools: Sequence[ToolSpec] = ()
    actions: Sequence[ActionKind] = ()
    catalogs: Sequence[CatalogProvider] = ()
    prompt_fragments: Sequence[PromptFragment] = ()
    fast_routes: Sequence[FastRoute] = ()
    attachment_tags: Tuple[str, ...] = ()

"""Process-wide registry of plugins.

Plugins register from ``AppConfig.ready()``; the order of registration (INSTALLED_APPS order) is the order of
tools, routes and same-``order`` prompt fragments. Tests can swap the plugin set with :func:`override`.
"""
from __future__ import annotations

import contextlib
from typing import Dict, Iterator, List, Optional, Sequence

from agent_helper.plugins import ActionKind, CatalogProvider, FastRoute, Plugin, PromptFragment, ToolSpec


class Registry:
    def __init__(self):
        self.plugins: List[Plugin] = []

    # --- registration
    def register(self, plugin: Plugin) -> Plugin:
        """Add a plugin. Re-registering the same plugin name replaces it (safe for repeated ready())."""
        if not isinstance(plugin, Plugin):
            raise TypeError('register() expects an agent_helper.plugins.Plugin')
        others = [p for p in self.plugins if p.name != plugin.name]
        taken_tools = {t.name for p in others for t in p.tools}
        taken_kinds = {a.kind for p in others for a in p.actions}
        for spec in plugin.tools:
            if spec.name in taken_tools:
                raise ValueError(f'tool {spec.name!r} is already registered by another plugin')
            taken_tools.add(spec.name)
        for kind in plugin.actions:
            if kind.kind in taken_kinds:
                raise ValueError(f'action kind {kind.kind!r} is already registered by another plugin')
            taken_kinds.add(kind.kind)
        replaced = [i for i, p in enumerate(self.plugins) if p.name == plugin.name]
        if replaced:
            self.plugins[replaced[0]] = plugin
        else:
            self.plugins.append(plugin)
        return plugin

    def check(self) -> List[str]:
        """Cross-plugin consistency problems (empty list = ok)."""
        kinds = {a.kind for a in self.actions()}
        errors = []
        for spec in self.tools():
            if not spec.read_only and spec.proposes not in kinds:
                errors.append(f'tool {spec.name!r} proposes unknown action kind {spec.proposes!r}')
        return errors

    # --- lookup
    def tools(self) -> List[ToolSpec]:
        return [t for p in self.plugins for t in p.tools]

    def tool(self, name: str) -> Optional[ToolSpec]:
        return next((t for t in self.tools() if t.name == name), None)

    def actions(self) -> List[ActionKind]:
        return [a for p in self.plugins for a in p.actions]

    def action(self, kind: str) -> Optional[ActionKind]:
        return next((a for a in self.actions() if a.kind == kind), None)

    def catalogs(self) -> List[CatalogProvider]:
        return [c for p in self.plugins for c in p.catalogs]

    def fragments(self) -> List[PromptFragment]:
        return [f for p in self.plugins for f in p.prompt_fragments]

    def routes(self) -> List[FastRoute]:
        routes = [r for p in self.plugins for r in p.fast_routes]
        return sorted(routes, key=lambda r: r.order)  # stable: same order keeps registration order

    def attachment_tags(self) -> Sequence[str]:
        return tuple(t for p in self.plugins for t in p.attachment_tags)


registry = Registry()


def register(plugin: Plugin) -> Plugin:
    return registry.register(plugin)


@contextlib.contextmanager
def override(plugins: Sequence[Plugin]) -> Iterator[Registry]:
    """Temporarily replace the registered plugins (tests)."""
    saved = registry.plugins
    registry.plugins = []
    try:
        for p in plugins:
            registry.register(p)
        yield registry
    finally:
        registry.plugins = saved


def by_name() -> Dict[str, Plugin]:
    return {p.name: p for p in registry.plugins}

"""ساخت مستندات پکیج agent_helper در agent_helper/docs (همراه wheel منتشر می‌شود).

اجرا: python packages/agent_helper/docs_src/build.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib  # noqa: E402
import pages_guide as G  # noqa: E402
import pages_ops as O  # noqa: E402
import pages_ref as R  # noqa: E402
import pages_start as S  # noqa: E402

BUILDERS = {
    'index': S.index, 'installation': S.installation, 'tutorial': S.tutorial, 'concepts': S.concepts,
    'configuration': S.configuration, 'plugins': G.plugins, 'tools': G.tools, 'actions': G.actions_page,
    'fast-routes': G.fast_routes, 'prompts': G.prompts, 'attachments': G.attachments, 'http-api': R.http_api,
    'frontend': R.frontend, 'python-api': R.python_api, 'settings-ref': R.settings_ref, 'security': O.security,
    'observability': O.observability, 'testing': O.testing, 'deployment': O.deployment,
    'troubleshooting': O.troubleshooting, 'changelog': O.changelog,
}


def main():
    assert set(BUILDERS) == {p[0] for p in lib.PAGES}, set(BUILDERS) ^ {p[0] for p in lib.PAGES}
    out = os.path.join(HERE, '..', 'agent_helper', 'docs')
    os.makedirs(out, exist_ok=True)
    sizes = {}
    for slug, build in BUILDERS.items():
        html = build()
        with open(os.path.join(out, f'{slug}.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        sizes[slug] = len(html)
    with open(os.path.join(out, 'style.css'), 'w', encoding='utf-8') as fh:
        fh.write(lib.CSS)
    print('ok', len(sizes), 'pages ->', os.path.normpath(out))


main()

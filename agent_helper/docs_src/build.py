"""ساخت مستندات پکیج agent_helper در agent_helper/docs (فارسی) و agent_helper/docs/en (انگلیسی)؛ همراه wheel منتشر می‌شود.

اجرا: python packages/agent_helper/docs_src/build.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib  # noqa: E402

MODULES = {'fa': ('pages_start', 'pages_guide', 'pages_ref', 'pages_ops'),
           'en': ('en_start', 'en_guide', 'en_ref', 'en_ops')}
NAMES = {'actions': 'actions_page', 'fast-routes': 'fast_routes', 'http-api': 'http_api', 'python-api': 'python_api',
         'settings-ref': 'settings_ref'}


def builders(lang):
    mods = [__import__(m) for m in MODULES[lang]]
    out = {}
    for slug, _t, _g in lib.PAGES:
        name = NAMES.get(slug, slug)
        out[slug] = next(getattr(m, name) for m in mods if hasattr(m, name))
    return out


def main():
    root = os.path.join(HERE, '..', 'agent_helper', 'docs')
    for lang, sub in (('fa', ''), ('en', 'en')):
        lib.LANG = lang
        out = os.path.join(root, sub)
        os.makedirs(out, exist_ok=True)
        for slug, build in builders(lang).items():
            with open(os.path.join(out, f'{slug}.html'), 'w', encoding='utf-8') as fh:
                fh.write(build())
        print('ok', lang, len(lib.PAGES), 'pages ->', os.path.normpath(out))
    lib.LANG = 'fa'
    with open(os.path.join(root, 'style.css'), 'w', encoding='utf-8') as fh:
        fh.write(lib.CSS)


main()

"""قالب مستندات پکیج agent_helper: ناوبری گروه‌بندی‌شده، فهرست «در این صفحه»، کد با دکمه‌ی کپی، حالت تیره."""
import html
import re

VERSION = '0.1.0b1'
STAGE = 'beta'          # pre-release: the API may still change before 1.0
LANG = 'fa'             # set by build.py: 'fa' (docs/) or 'en' (docs/en/)

UI = {
    'fa': {'dir': 'rtl', 'search': 'جست‌وجو در فهرست…', 'copy': 'کپی', 'copied': 'کپی شد', 'toc': 'در این صفحه',
           'prev': 'قبلی', 'next': 'بعدی', 'footer': 'مستندات پکیج', 'other': 'English', 'other_href': 'en/{slug}.html',
           'css': 'style.css', 'beta': 'بتا',
           'banner': '<b>نسخه‌ی بتا ({v}).</b> این پکیج هنوز به‌صورت پایدار منتشر نشده است؛ تا نسخه‌ی 1.0 ممکن است API و تنظیمات تغییر کنند.'},
    'en': {'dir': 'ltr', 'search': 'Filter pages…', 'copy': 'Copy', 'copied': 'Copied', 'toc': 'On this page',
           'prev': 'Previous', 'next': 'Next', 'footer': 'package documentation', 'other': 'فارسی', 'other_href': '../{slug}.html',
           'css': '../style.css', 'beta': 'beta',
           'banner': '<b>Beta release ({v}).</b> This package is not a stable release yet; the API and settings may change before 1.0.'},
}

# (slug, title, group)
PAGES = [
    ('index', 'معرفی', 'شروع'),
    ('installation', 'نصب', 'شروع'),
    ('tutorial', 'آموزش: از صفر تا اولین گفتگو', 'شروع'),
    ('concepts', 'مفاهیم و معماری', 'راهنما'),
    ('configuration', 'پیکربندی', 'راهنما'),
    ('plugins', 'نوشتن افزونه', 'راهنما'),
    ('tools', 'ابزارها (ToolSpec)', 'راهنما'),
    ('actions', 'اقدام معلق (ActionKind)', 'راهنما'),
    ('fast-routes', 'مسیر سریع و Jev', 'راهنما'),
    ('prompts', 'پرامپت و انتخاب ابزار', 'راهنما'),
    ('attachments', 'پیوست تصویر', 'راهنما'),
    ('http-api', 'API و رویدادهای SSE', 'مرجع'),
    ('frontend', 'اتصال رابط کاربری', 'مرجع'),
    ('python-api', 'مرجع پایتون', 'مرجع'),
    ('settings-ref', 'مرجع تنظیمات', 'مرجع'),
    ('security', 'مدل امنیتی', 'عملیات'),
    ('observability', 'لاگ، ادمین و پایش', 'عملیات'),
    ('testing', 'تست', 'عملیات'),
    ('deployment', 'استقرار', 'عملیات'),
    ('troubleshooting', 'عیب‌یابی و پرسش‌ها', 'عملیات'),
    ('changelog', 'تغییرات', 'عملیات'),
]

PAGES_EN = [
    ('index', 'Introduction', 'Getting started'),
    ('installation', 'Installation', 'Getting started'),
    ('tutorial', 'Tutorial: zero to first chat', 'Getting started'),
    ('concepts', 'Concepts and architecture', 'Guide'),
    ('configuration', 'Configuration', 'Guide'),
    ('plugins', 'Writing a plugin', 'Guide'),
    ('tools', 'Tools (ToolSpec)', 'Guide'),
    ('actions', 'Pending actions (ActionKind)', 'Guide'),
    ('fast-routes', 'Fast path and Jev', 'Guide'),
    ('prompts', 'Prompt and tool selection', 'Guide'),
    ('attachments', 'Image attachments', 'Guide'),
    ('http-api', 'HTTP API and SSE events', 'Reference'),
    ('frontend', 'Connecting a frontend', 'Reference'),
    ('python-api', 'Python reference', 'Reference'),
    ('settings-ref', 'Settings reference', 'Reference'),
    ('security', 'Security model', 'Operations'),
    ('observability', 'Logs, admin and monitoring', 'Operations'),
    ('testing', 'Testing', 'Operations'),
    ('deployment', 'Deployment', 'Operations'),
    ('troubleshooting', 'Troubleshooting and FAQ', 'Operations'),
    ('changelog', 'Changelog', 'Operations'),
]


def pages():
    return PAGES_EN if LANG == 'en' else PAGES

CSS = r"""
:root{--bg:#ffffff;--side:#f7f8fa;--ink:#1f2328;--muted:#656d76;--line:#e4e7eb;--pri:#2f5bd3;--pri2:#eef3ff;
--code:#0d1117;--codeink:#e6edf3;--ic:#f1f3f5;--ok:#1a7f37;--ok2:#ecfdf3;--warn:#9a6700;--warn2:#fff8e5;--bad:#cf222e;--bad2:#ffefef;
--kw:#ff7b72;--str:#a5d6ff;--com:#8b949e;--fn:#d2a8ff}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--side:#111722;--ink:#e6edf3;--muted:#8d96a0;--line:#232b36;--pri:#7aa2ff;--pri2:#162038;
--code:#010409;--ic:#1b2230;--ok:#3fb950;--ok2:#0f2418;--warn:#d29922;--warn2:#2a2210;--bad:#f85149;--bad2:#2c1215}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Vazirmatn","Segoe UI",Tahoma,sans-serif;line-height:1.95;font-size:15.5px}
a{color:var(--pri);text-decoration:none}a:hover{text-decoration:underline}
header.top{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:14px;height:56px;padding:0 20px;border-bottom:1px solid var(--line);background:var(--bg)}
header.top .brand{font-weight:800;font-size:17px;color:var(--ink)}header.top .ver{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:0 8px}
header.top .sp{flex:1}header.top input{width:min(260px,40vw);border:1px solid var(--line);background:var(--side);color:var(--ink);border-radius:8px;padding:6px 10px;font:inherit;font-size:13px}
.wrap{display:grid;grid-template-columns:250px minmax(0,1fr) 210px;min-height:calc(100vh - 56px)}
nav.side{background:var(--side);border-inline-end:1px solid var(--line);padding:18px 12px;position:sticky;top:56px;height:calc(100vh - 56px);overflow:auto}
nav.side h4{margin:16px 10px 4px;font-size:12px;color:var(--muted);font-weight:700}
nav.side a{display:block;padding:5px 10px;border-radius:7px;color:var(--ink);font-size:14px}
nav.side a.on{background:var(--pri2);color:var(--pri);font-weight:700}nav.side a:hover{background:var(--pri2);text-decoration:none}
main{padding:30px clamp(16px,4vw,48px) 60px;max-width:900px;width:100%}
aside.toc{position:sticky;top:56px;height:calc(100vh - 56px);overflow:auto;padding:28px 14px;font-size:13px;border-inline-start:1px solid var(--line)}
aside.toc b{display:block;color:var(--muted);margin-bottom:6px}aside.toc a{display:block;color:var(--muted);padding:2px 0}aside.toc a.h3{padding-inline-start:12px}
.crumb{color:var(--muted);font-size:13px;margin-bottom:4px}
h1{font-size:30px;margin:0 0 8px;line-height:1.45}.lead{color:var(--muted);font-size:16.5px;margin:0 0 26px}
h2{font-size:22px;margin:40px 0 10px;padding-top:8px;border-top:1px solid var(--line)}h3{font-size:17px;margin:26px 0 6px}
h2 .anchor,h3 .anchor{opacity:0;margin-inline-start:6px;font-size:.8em}h2:hover .anchor,h3:hover .anchor{opacity:1}
p{margin:8px 0}ul,ol{padding-inline-start:24px;margin:8px 0}li{margin:3px 0}
code{direction:ltr;unicode-bidi:isolate;background:var(--ic);padding:1px 6px;border-radius:6px;font-size:13px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.pre{position:relative;margin:12px 0}
pre{direction:ltr;text-align:left;background:var(--code);color:var(--codeink);padding:30px 16px 14px;border-radius:10px;overflow:auto;font-size:13px;line-height:1.65;margin:0;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
pre code{background:none;padding:0;color:inherit;font-size:inherit}
.pre .lang{position:absolute;top:6px;left:12px;font-size:11px;color:#8b949e;direction:ltr}
.pre button{position:absolute;top:6px;right:8px;font:inherit;font-size:11px;background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:1px 8px;cursor:pointer}
.tk-k{color:var(--kw)}.tk-s{color:var(--str)}.tk-c{color:var(--com);font-style:italic}.tk-f{color:var(--fn)}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:start;vertical-align:top}th{background:var(--side);font-weight:700;white-space:nowrap}
.adm{border-radius:10px;padding:10px 14px;margin:14px 0;border-inline-start:4px solid}
.adm b.t{display:block;margin-bottom:2px}
.note{background:var(--pri2);border-color:var(--pri)}.tip{background:var(--ok2);border-color:var(--ok)}.warn{background:var(--warn2);border-color:var(--warn)}.danger{background:var(--bad2);border-color:var(--bad)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:16px 0}
.cards a{display:block;border:1px solid var(--line);border-radius:12px;padding:14px 16px;color:var(--ink)}.cards a:hover{border-color:var(--pri);text-decoration:none}
.cards a b{display:block}.cards a span{color:var(--muted);font-size:13px}
.sig{direction:ltr;text-align:left;border:1px solid var(--line);border-radius:10px;padding:8px 12px;background:var(--side);font-family:ui-monospace,Consolas,monospace;font-size:13.5px;margin:14px 0 6px;overflow-x:auto}
.steps{counter-reset:s;list-style:none;padding:0}.steps>li{counter-increment:s;position:relative;padding-inline-start:40px;margin:14px 0}
.steps>li:before{content:counter(s);position:absolute;inset-inline-start:0;top:0;width:28px;height:28px;border-radius:50%;background:var(--pri);color:#fff;display:grid;place-items:center;font-size:13px;font-weight:700}
.pn{display:flex;justify-content:space-between;gap:10px;margin-top:48px;padding-top:16px;border-top:1px solid var(--line)}
.pn a{border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:14px}.pn small{display:block;color:var(--muted);font-size:12px}
footer{color:var(--muted);font-size:12.5px;margin-top:30px}
mark{background:#ffe58f;color:#000;border-radius:3px}
html[lang=en] body{font-family:system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.7}
header.top .beta{font-size:11px;font-weight:700;color:var(--warn);background:var(--warn2);border:1px solid var(--warn);border-radius:999px;padding:0 8px;text-transform:uppercase}
header.top .lang{font-size:13px;border:1px solid var(--line);border-radius:8px;padding:3px 10px}
.beta-banner{background:var(--warn2);border:1px solid var(--warn);border-radius:10px;padding:8px 14px;margin:0 0 18px;font-size:14px}
@media (max-width:1100px){.wrap{grid-template-columns:230px minmax(0,1fr)}aside.toc{display:none}}
@media (max-width:760px){.wrap{grid-template-columns:minmax(0,1fr)}nav.side{position:static;height:auto;border-inline-end:none;border-bottom:1px solid var(--line)}header.top input{display:none}}
"""

JS = r"""
document.querySelectorAll('.pre button').forEach(b=>b.onclick=()=>{const t=b.textContent;navigator.clipboard.writeText(b.parentElement.querySelector('code').innerText).then(()=>{b.textContent=b.dataset.done;setTimeout(()=>b.textContent=t,1200)})});
const q=document.getElementById('q');if(q){q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();document.querySelectorAll('nav.side a').forEach(a=>{a.style.display=!v||a.textContent.toLowerCase().includes(v)||(a.dataset.k||'').includes(v)?'':'none'})})}
"""

_LATIN = re.compile(r"[A-Za-z_][A-Za-z0-9_\-./:+@%#=]*(?: [A-Za-z_][A-Za-z0-9_\-./:+@%#=]*)*")
_SKIP = ("pre", "code", "style", "title", "script", "div class=\"sig\"")


def fix_bidi(doc):
    """متن لاتین وسط فارسی را با bdi ایزوله می‌کند (جز داخل pre/code/style/script)"""
    out, skip = [], 0
    for tok in re.split(r"(<[^>]*>)", doc):
        if tok.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", tok)
            if m and m.group(2).lower() in ("pre", "code", "style", "title", "script"):
                skip = max(0, skip + (-1 if m.group(1) else 1))
            out.append(tok)
            continue
        if skip or not tok.strip():
            out.append(tok)
            continue
        parts = re.split(r"(&[a-zA-Z#0-9]+;)", tok)
        out.append("".join(p if p.startswith("&") and p.endswith(";")
                           else _LATIN.sub(lambda m: f'<bdi dir="ltr">{m.group(0)}</bdi>', p) for p in parts))
    return "".join(out)


def e(s):
    return html.escape(s)


_PY_KW = r"\b(def|class|return|import|from|as|if|else|elif|for|in|not|and|or|None|True|False|with|try|except|raise|lambda|yield|await|async|const|let|function|new)\b"


_TOKEN = {
    'python': re.compile(r"(?P<c>#[^\n]*)|(?P<s>'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")|(?P<k>" + _PY_KW[2:-2] + r")\b"),
    'js': re.compile(r"(?P<c>//[^\n]*)|(?P<s>'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`[^`]*`)|(?P<k>" + _PY_KW[2:-2] + r")\b"),
}


def _highlight(src, lang):
    """رنگ‌آمیزی ساده: توکن‌ها روی متن خام پیدا و جدا escape می‌شوند"""
    rx = _TOKEN.get(lang)
    if rx is None:
        return e(src)
    out, pos = [], 0
    for m in rx.finditer(src):
        if m.group('k') and (m.start() > 0 and (src[m.start() - 1].isalnum() or src[m.start() - 1] == '_')):
            continue
        out.append(e(src[pos:m.start()]))
        cls = 'tk-c' if m.group('c') else 'tk-s' if m.group('s') else 'tk-k'
        out.append(f'<span class="{cls}">{e(m.group(0))}</span>')
        pos = m.end()
    out.append(e(src[pos:]))
    return ''.join(out)


def code(src, lang='python'):
    src = src.strip('\n')
    label = {'python': 'Python', 'bash': 'Shell', 'js': 'JavaScript', 'json': 'JSON', 'text': '', 'http': 'HTTP'}.get(lang, lang)
    ui = UI[LANG]
    return (f'<div class="pre"><span class="lang">{label}</span><button type="button" data-done="{ui["copied"]}">{ui["copy"]}</button>'
            f'<pre><code>{_highlight(src, lang)}</code></pre></div>')


def table(head, rows):
    h = ''.join(f'<th>{c}</th>' for c in head)
    b = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def adm(kind, title, body):
    return f'<div class="adm {kind}"><b class="t">{title}</b>{body}</div>'


def sig(text):
    return f'<div class="sig">{e(text)}</div>'


def _slugify(text, used):
    base = re.sub(r'<[^>]+>', '', text)
    base = re.sub(r'[^\w؀-ۿ]+', '-', base).strip('-').lower()[:50] or 's'
    slug, i = base, 2
    while slug in used:
        slug, i = f'{base}-{i}', i + 1
    used.add(slug)
    return slug


def _with_anchors(body):
    used, toc = set(), []

    def repl(m):
        level, inner = m.group(1), m.group(2)
        slug = _slugify(inner, used)
        toc.append((level, slug, re.sub(r'<[^>]+>', '', inner)))
        return f'<h{level} id="{slug}">{inner}<a class="anchor" href="#{slug}">#</a></h{level}>'
    body = re.sub(r'<h([23])>(.*?)</h\1>', repl, body)
    return body, toc


def page(slug, title, lead, body, keywords=''):
    ui, plist = UI[LANG], pages()
    idx = [p[0] for p in plist].index(slug)
    group = plist[idx][2]
    nav, last = '', None
    for s, t, g in plist:
        if g != last:
            nav += f'<h4>{g}</h4>'
            last = g
        nav += f'<a class="{"on" if s == slug else ""}" href="{s}.html">{t}</a>'
    body, toc = _with_anchors(body)
    toc_html = ''.join(f'<a class="h{lv}" href="#{s}">{t}</a>' for lv, s, t in toc)
    back, fwd = ('→', '←') if ui['dir'] == 'rtl' else ('←', '→')
    prev_ = f'<a href="{plist[idx-1][0]}.html"><small>{ui["prev"]}</small>{back} {plist[idx-1][1]}</a>' if idx > 0 else '<span></span>'
    next_ = f'<a href="{plist[idx+1][0]}.html"><small>{ui["next"]}</small>{plist[idx+1][1]} {fwd}</a>' if idx < len(plist) - 1 else '<span></span>'
    banner = f'<div class="beta-banner" role="note">{ui["banner"].format(v=VERSION)}</div>' if STAGE else ''
    stage = f'<span class="beta">{ui["beta"]}</span>' if STAGE else ''
    other = 'en' if LANG == 'fa' else 'fa'
    doc = f'''<!doctype html>
<html lang="{LANG}" dir="{ui['dir']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — agent-helper</title><meta name="description" content="{e(lead)}"><link rel="stylesheet" href="{ui['css']}"></head>
<body><header class="top"><a class="brand" href="index.html">agent-helper</a><span class="ver">v{VERSION}</span>{stage}<span class="sp"></span>
<a class="lang" href="{ui['other_href'].format(slug=slug)}" hreflang="{other}" lang="{other}">{ui['other']}</a>
<input id="q" type="search" placeholder="{ui['search']}"></header>
<div class="wrap"><nav class="side">{nav}</nav>
<main><div class="crumb">{group}</div>{banner}<h1>{title}</h1><p class="lead">{lead}</p>{body}
<div class="pn">{prev_}{next_}</div><footer>agent-helper {VERSION} ({STAGE or 'stable'}) · {ui['footer']}</footer></main>
<aside class="toc"><b>{ui['toc']}</b>{toc_html}</aside></div><script>{JS}</script></body></html>'''
    return fix_bidi(doc) if LANG == 'fa' else doc

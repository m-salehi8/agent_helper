"""نسخه‌ی تک‌فایلی مستندات پکیج برای انتشار به‌صورت Artifact (ناوبری درون‌صفحه‌ای با #slug).

اجرا: python packages/agent_helper/docs_src/artifact.py <خروجی.html> [fa|en]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lib  # noqa: E402

CAPTURED = {}
LANG = sys.argv[2] if len(sys.argv) > 2 else 'fa'
lib.LANG = LANG


def _capture(slug, title, lead, body, keywords=''):
    CAPTURED[slug] = (title, lead, body)
    return ''


lib.page = _capture
MODS = {'fa': ('pages_start', 'pages_guide', 'pages_ref', 'pages_ops'), 'en': ('en_start', 'en_guide', 'en_ref', 'en_ops')}[LANG]
NAMES = {'actions': 'actions_page', 'fast-routes': 'fast_routes', 'http-api': 'http_api', 'python-api': 'python_api',
         'settings-ref': 'settings_ref'}
_mods = []
for mod in MODS:
    m = __import__(mod)
    m.page = _capture
    _mods.append(m)
for _slug, _t, _g in lib.PAGES:
    _name = NAMES.get(_slug, _slug)
    next(getattr(m, _name) for m in _mods if hasattr(m, _name))()  # page() is replaced by _capture, so nothing is written

CSS = """
/* Layout: sticky top bar, right-hand page index, one reading column, in-page table of contents on wide screens */
:root{--bg:#fbfbfd;--side:#f2f3f8;--ink:#1c2030;--muted:#5e6577;--line:#e1e3ec;--pri:#3448c5;--pri2:#e9ecfb;
--code:#121625;--codeink:#e4e8f4;--ic:#eceef6;--ok:#17703a;--ok2:#e8f6ee;--warn:#8a5a00;--warn2:#fdf4df;--bad:#b42330;--bad2:#fcecee;
--kw:#ff8f86;--str:#a9d4ff;--com:#8a93a8;--codebtn:#262c3f;--codebtnink:#cfd6e8;
--f-body:"Vazirmatn",Tahoma,"Segoe UI",sans-serif;--f-mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e111a;--side:#131826;--ink:#e3e7f2;--muted:#959db1;--line:#252c3d;--pri:#8fa2ff;--pri2:#1a2140;
--code:#080b13;--ic:#1c2233;--ok:#4cc27a;--ok2:#10261a;--warn:#e0aa3e;--warn2:#2a2210;--bad:#f2707a;--bad2:#2c1418;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0e111a;--side:#131826;--ink:#e3e7f2;--muted:#959db1;--line:#252c3d;--pri:#8fa2ff;--pri2:#1a2140;
--code:#080b13;--ic:#1c2233;--ok:#4cc27a;--ok2:#10261a;--warn:#e0aa3e;--warn2:#2a2210;--bad:#f2707a;--bad2:#2c1418;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);line-height:1.95;font-size:15.5px}
:root[lang=en] body{font-family:system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.7}
a{color:var(--pri);text-decoration:none}a:hover{text-decoration:underline}
a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--pri);outline-offset:2px}
header.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;display:flex;align-items:center;gap:12px;min-height:54px;padding-inline:18px;border-bottom:1px solid var(--line);background:var(--bg)}
header.top .brand{font-weight:800;font-size:17px;color:var(--ink);direction:ltr}
header.top .ver{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding-inline:8px;direction:ltr}
header.top .sp{flex:1}
header.top input{width:min(240px,38vw);border:1px solid var(--line);background:var(--side);color:var(--ink);border-radius:8px;padding:6px 10px;font:inherit;font-size:13px}
.wrap{display:grid;grid-template-columns:240px minmax(0,1fr) 200px}
nav.side{background:var(--side);border-inline-end:1px solid var(--line);padding:16px 10px;position:sticky;top:calc(54px + env(safe-area-inset-top,0px));height:calc(100vh - 54px);overflow:auto}
nav.side h4{margin:14px 10px 4px;font-size:12px;color:var(--muted);font-weight:700;letter-spacing:.02em}
nav.side a{display:block;padding:4px 10px;border-radius:7px;color:var(--ink);font-size:14px}
nav.side a.on{background:var(--pri2);color:var(--pri);font-weight:700}nav.side a:hover{background:var(--pri2);text-decoration:none}
main{min-width:0;padding:28px clamp(16px,4vw,48px) 60px;max-width:900px;width:100%}
aside.toc{position:sticky;top:calc(54px + env(safe-area-inset-top,0px));height:calc(100vh - 54px);overflow:auto;padding:26px 14px;font-size:13px;border-inline-start:1px solid var(--line)}
aside.toc b{display:block;color:var(--muted);margin-bottom:6px}aside.toc a{display:block;color:var(--muted);padding:2px 0}aside.toc a.h3{padding-inline-start:12px}
section.doc{display:block}section.doc[hidden]{display:none!important}
.crumb{color:var(--muted);font-size:13px;margin-bottom:4px}
h1{font-size:29px;margin:0 0 8px;line-height:1.45;text-wrap:balance}.lead{color:var(--muted);font-size:16.5px;margin:0 0 26px;max-width:65ch}
h2{font-size:21px;margin:38px 0 10px;padding-top:8px;border-top:1px solid var(--line);text-wrap:balance}h3{font-size:16.5px;margin:24px 0 6px}
h2 .anchor,h3 .anchor{opacity:0;margin-inline-start:6px;font-size:.8em}h2:hover .anchor,h3:hover .anchor{opacity:1}
p{margin:8px 0}ul,ol{padding-inline-start:24px;margin:8px 0}li{margin:3px 0}
code{direction:ltr;unicode-bidi:isolate;background:var(--ic);padding:1px 6px;border-radius:6px;font-size:13px;font-family:var(--f-mono)}
.pre{position:relative;margin:12px 0}
pre{direction:ltr;text-align:left;background:var(--code);color:var(--codeink);padding:30px 16px 14px;border-radius:10px;overflow-x:auto;font-size:13px;line-height:1.65;margin:0;font-family:var(--f-mono)}
pre code{background:none;padding:0;color:inherit;font-size:inherit}
.pre .lang{position:absolute;top:6px;left:12px;font-size:11px;color:var(--com);direction:ltr}
.pre button{position:absolute;top:6px;right:8px;font:inherit;font-size:11px;background:var(--codebtn);color:var(--codebtnink);border:1px solid var(--codebtn);border-radius:6px;padding:1px 8px;cursor:pointer}
.tk-k{color:var(--kw)}.tk-s{color:var(--str)}.tk-c{color:var(--com);font-style:italic}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;display:block;overflow-x:auto;font-variant-numeric:tabular-nums}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:start;vertical-align:top}th{background:var(--side);font-weight:700;white-space:nowrap}
.adm{border-radius:10px;padding:10px 14px;margin:14px 0;border-inline-start:4px solid}.adm b.t{display:block;margin-bottom:2px}
.note{background:var(--pri2);border-color:var(--pri)}.tip{background:var(--ok2);border-color:var(--ok)}.warn{background:var(--warn2);border-color:var(--warn)}.danger{background:var(--bad2);border-color:var(--bad)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.cards a{display:block;border:1px solid var(--line);border-radius:12px;padding:14px 16px;color:var(--ink)}.cards a:hover{border-color:var(--pri);text-decoration:none}
.cards a b{display:block}.cards a span{color:var(--muted);font-size:13px}
.sig{direction:ltr;text-align:left;border:1px solid var(--line);border-radius:10px;padding:8px 12px;background:var(--side);font-family:var(--f-mono);font-size:13.5px;margin:14px 0 6px;overflow-x:auto}
.steps{counter-reset:s;list-style:none;padding:0}.steps>li{counter-increment:s;position:relative;padding-inline-start:40px;margin:14px 0;min-width:0}
.steps>li:before{content:counter(s);position:absolute;inset-inline-start:0;top:0;width:28px;height:28px;border-radius:50%;background:var(--pri);color:var(--bg);display:grid;place-items:center;font-size:13px;font-weight:700}
.pn{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-top:46px;padding-top:16px;border-top:1px solid var(--line)}
.pn a{border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:14px}.pn small{display:block;color:var(--muted);font-size:12px}
footer{color:var(--muted);font-size:12.5px;margin-top:28px}
header.top .beta{font-size:11px;font-weight:700;color:var(--warn);background:var(--warn2);border:1px solid var(--warn);border-radius:999px;padding-inline:8px;text-transform:uppercase}
.beta-banner{background:var(--warn2);border:1px solid var(--warn);border-radius:10px;padding:8px 14px;margin:0 0 18px;font-size:14px}
@media (max-width:1100px){.wrap{grid-template-columns:220px minmax(0,1fr)}aside.toc{display:none}}
@media (max-width:760px){.wrap{grid-template-columns:minmax(0,1fr)}nav.side{position:static;height:auto;border-inline-end:none;border-bottom:1px solid var(--line)}header.top input{width:120px}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

JS = r"""
(function(){
  const pages=[...document.querySelectorAll('section.doc')], links=[...document.querySelectorAll('nav.side a')];
  const toc=document.getElementById('toc');
  function show(slug, anchor){
    const sec=document.getElementById('p-'+slug); if(!sec) return false;
    pages.forEach(p=>p.hidden=p!==sec);
    links.forEach(a=>a.classList.toggle('on',a.dataset.slug===slug));
    toc.innerHTML='<b>'+toc.dataset.title+'</b>'+[...sec.querySelectorAll('h2,h3')].map(h=>'<a class="'+h.tagName.toLowerCase()+'" href="#'+h.id+'">'+h.textContent.replace(/#$/,'')+'</a>').join('');
    if(anchor){const t=document.getElementById(anchor); if(t) t.scrollIntoView();} else window.scrollTo(0,0);
    return true;
  }
  function route(){
    const h=decodeURIComponent(location.hash.slice(1));
    if(!h){show('index');return;}
    if(show(h)) return;
    const el=document.getElementById(h);
    if(el){const sec=el.closest('section.doc'); if(sec) show(sec.id.slice(2), h);} else show('index');
  }
  window.addEventListener('hashchange',route); route();
  document.querySelectorAll('.pre button').forEach(b=>b.addEventListener('click',()=>{
    const code=b.parentElement.querySelector('code');
    const t=b.textContent,done=()=>{b.textContent=b.dataset.done;setTimeout(()=>b.textContent=t,1200)};
    try{navigator.clipboard.writeText(code.innerText).then(done,()=>sel(code));}catch(e){sel(code);}
  }));
  function sel(node){const r=document.createRange();r.selectNodeContents(node);const s=getSelection();s.removeAllRanges();s.addRange(r);}
  const q=document.getElementById('q');
  q.addEventListener('input',()=>{const v=q.value.trim();
    links.forEach(a=>{const sec=document.getElementById('p-'+a.dataset.slug);
      a.hidden=!!v && !a.textContent.toLowerCase().includes(v.toLowerCase()) && !(sec && sec.textContent.toLowerCase().includes(v.toLowerCase()));});});
})();
"""


def _relink(body, slug):
    """لینک‌های بین صفحه‌ها به #slug، و شناسه‌ی سرتیترها یکتا در کل سند"""
    body = re.sub(r'href="([a-z0-9-]+)\.html#([^"]+)"', lambda m: f'href="#{m.group(1)}--{m.group(2)}"', body)
    body = re.sub(r'href="([a-z0-9-]+)\.html"', r'href="#\1"', body)
    body = re.sub(r'(<h[23] id=")', rf'\1{slug}--', body)
    body = re.sub(r'(<a class="anchor" href="#)', rf'\1{slug}--', body)
    return body


def main(out_path):
    ui = lib.UI[LANG]
    back, fwd = ('→', '←') if ui['dir'] == 'rtl' else ('←', '→')
    banner = f'<div class="beta-banner" role="note">{ui["banner"].format(v=lib.VERSION)}</div>' if lib.STAGE else ''
    nav, last, sections = '', None, ''
    for i, (slug, _title, group) in enumerate(lib.PAGES_EN if LANG == 'en' else lib.PAGES):
        plist = lib.pages()
        title, lead, body = CAPTURED[slug]
        if group != last:
            nav += f'<h4>{group}</h4>'
            last = group
        nav += f'<a href="#{slug}" data-slug="{slug}">{_title}</a>'
        body, _ = lib._with_anchors(body)
        body = _relink(body, slug)
        prev_ = (f'<a href="#{plist[i-1][0]}"><small>{ui["prev"]}</small>{back} {plist[i-1][1]}</a>' if i else '<span></span>')
        next_ = (f'<a href="#{plist[i+1][0]}"><small>{ui["next"]}</small>{plist[i+1][1]} {fwd}</a>' if i < len(plist) - 1 else '<span></span>')
        sections += (f'<section class="doc" id="p-{slug}" {"" if slug == "index" else "hidden"}><div class="crumb">{group}</div>{banner}'
                     f'<h1>{title}</h1><p class="lead">{lead}</p>{body}<div class="pn">{prev_}{next_}</div></section>')
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700;800&display=swap">') if LANG == 'fa' else ''
    footer = ('مستندات فنی پکیج (هسته‌ی عمومی دستیار هوشمند برای Django)' if LANG == 'fa'
              else 'Technical documentation (generic assistant core for Django)')
    stage = f'<span class="beta">{ui["beta"]}</span>' if lib.STAGE else ''
    doc = f'''<title>{'agent-helper English Docs' if LANG == 'en' else 'agent-helper Docs'}</title>
<script>document.documentElement.lang='{LANG}';document.documentElement.dir='{ui['dir']}';</script>
{fonts}
<style>{CSS}</style>
<header class="top"><a class="brand" href="#index">agent-helper</a><span class="ver">v{lib.VERSION}</span>{stage}<span class="sp"></span>
<input id="q" type="search" aria-label="{ui['search']}" placeholder="{ui['search']}"></header>
<div class="wrap" dir="{ui['dir']}"><nav class="side">{nav}</nav>
<main>{sections}<footer>agent-helper {lib.VERSION} ({lib.STAGE or 'stable'}) · {footer}</footer></main>
<aside class="toc" id="toc" data-title="{ui['toc']}"></aside></div>
<script>{JS}</script>'''
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(lib.fix_bidi(doc) if LANG == 'fa' else doc)
    print('ok', out_path, len(doc))


main(sys.argv[1])

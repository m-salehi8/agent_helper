"""افزونه‌ی نمونه‌ی «یادداشت من»: کوچک‌ترین افزونه‌ی کامل روی هسته‌ی agent_helper.

- دو ابزار فقط‌خواندنی: list_my_notes و get_leave_balance
- یک ابزار پیشنهاد: propose_add_note ⇒ اقدام معلق add_note (یادداشت فقط با دکمه‌ی تایید کاربر ذخیره می‌شود)
- یک مسیر سریع: «چند روز مرخصی دارم؟» بدون LLM
- یک قطعه‌ی پرامپت
"""
import re

from django.conf import settings

from agent_helper import actions
from agent_helper.plugins import ActionKind, FastRoute, Plugin, PromptFragment, ToolSpec

MAX_NOTE = 500


def _conf(key, default):
    return (getattr(settings, 'AGENT_HELPER_DEMO', None) or {}).get(key, default)


# ----------------------------------------------------------------------------- ابزارها

def list_my_notes(user, args, ctx):
    from agent_helper_demo.models import DemoNote
    try:
        limit = max(1, min(int(args.get('limit') or 10), 50))
    except (TypeError, ValueError):
        limit = 10
    notes = [{'id': n.id, 'text': n.text, 'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')}
             for n in DemoNote.objects.filter(user=user)[:limit]]
    return {'count': len(notes), 'notes': notes, 'message': '' if notes else 'یادداشتی ندارید.'}


def leave_balance(user) -> dict:
    """موجودی مرخصی نمونه (بدون منبع واقعی): سهم سالانه منهای تعداد یادداشت‌هایی که با «مرخصی» شروع می‌شوند"""
    from agent_helper_demo.models import DemoNote
    yearly = int(_conf('YEARLY_LEAVE_DAYS', 26))
    used = DemoNote.objects.filter(user=user, text__startswith='مرخصی').count()
    return {'yearly_days': yearly, 'used_days': used, 'remaining_days': max(0, yearly - used)}


def get_leave_balance(user, args, ctx):
    return leave_balance(user)


def propose_add_note(user, args, ctx):
    text = str(args.get('text') or '').strip()
    if not text:
        return {'error': 'متن یادداشت خالی است.'}
    if len(text) > MAX_NOTE:
        return {'error': f'یادداشت حداکثر {MAX_NOTE} نویسه است.'}
    action = ctx.propose('add_note', {'text': text})
    return {'status': 'ready', 'action_id': action.id,
            'message': 'پیش‌نویس یادداشت آماده است؛ کاربر باید با دکمه تایید کند. هرگز نگو ذخیره شد.'}


def _notes_event(result):
    return [{'event': 'note_list', 'items': result['notes'], 'count': result['count']}] if result.get('notes') else []


TOOLS = [
    ToolSpec(name='list_my_notes', description='فهرست یادداشت‌های خود کاربر (جدیدترین اول).',
             json_schema={'type': 'object', 'properties': {'limit': {'type': 'integer', 'description': 'حداکثر تعداد (پیش‌فرض ۱۰)'}},
                          'required': []},
             handler=list_my_notes, tags=('notes',), status='در حال خواندن یادداشت‌های شما...', events=_notes_event),
    ToolSpec(name='get_leave_balance', description='موجودی مرخصی سالانه‌ی کاربر (سهم، استفاده‌شده، باقی‌مانده به روز).',
             json_schema={'type': 'object', 'properties': {}, 'required': []},
             handler=get_leave_balance, tags=('leave',), status='در حال محاسبه‌ی موجودی مرخصی...'),
    ToolSpec(name='propose_add_note', description='پیش‌نویس یک یادداشت جدید برای کاربر؛ ذخیره نمی‌کند، فقط کارت تایید می‌سازد.',
             json_schema={'type': 'object', 'properties': {'text': {'type': 'string', 'description': 'متن یادداشت'}},
                          'required': ['text']},
             handler=propose_add_note, read_only=False, proposes='add_note', tags=('notes',),
             status='در حال آماده‌سازی پیش‌نویس یادداشت...'),
]


# ----------------------------------------------------------------------------- اقدام معلق

def execute_add_note(user, action, params):
    from agent_helper_demo.models import DemoNote
    note = DemoNote.objects.create(user=user, text=action.payload['text'][:MAX_NOTE])
    actions.audit(user, action, 'created', 'یادداشت ذخیره شد', node_id=note.id)
    return {'status': 'confirmed', 'message': 'یادداشت ذخیره شد.', 'action_id': action.id,
            'results': [{'note_id': note.id, 'status': 'success'}], 'status_code': 200}


ADD_NOTE = ActionKind(kind='add_note', execute=execute_add_note, audit_label='یادداشت',
                      preview=lambda payload: {'kind': 'add_note', 'text': payload['text'], 'items': [], 'count': 1},
                      propose_schema={'type': 'object', 'required': ['text'], 'properties': {'text': {'type': 'string'}}})


# ----------------------------------------------------------------------------- مسیر سریع و پرامپت

LEAVE_RE = re.compile(r'مرخصی')
LEAVE_ASK_RE = re.compile(r'چند|چقدر|موجودی|مانده|باقی')


def leave_route(req):
    """«چند روز مرخصی دارم؟» ⇒ ابزار مستقیم، بدون LLM"""
    result = req.run_tool('get_leave_balance', {})
    fa = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return req.reply(f'از {str(result["yearly_days"]).translate(fa)} روز مرخصی سالانه، '
                     f'{str(result["remaining_days"]).translate(fa)} روز برایتان مانده است.')


ROUTES = [FastRoute(name='leave', handler=leave_route, tags=('leave',),
                    guard=lambda text: bool(LEAVE_RE.search(text or '') and LEAVE_ASK_RE.search(text or '')))]

FRAGMENTS = [PromptFragment(key='demo.notes', order=60, tags=('notes',), text=(
    'یادداشت‌ها: برای دیدن یادداشت‌ها list_my_notes و برای افزودن propose_add_note را صدا بزن. '
    'افزودن فقط پیش‌نویس می‌سازد؛ کاربر با دکمه ذخیره می‌کند. هرگز نگو یادداشت ذخیره شد.'))]

PLUGIN = Plugin(name='demo', tools=TOOLS, actions=[ADD_NOTE], prompt_fragments=FRAGMENTS, fast_routes=ROUTES)

# agent-helper-demo

افزونه‌ی نمونه‌ی «یادداشت من» برای `agent_helper` و نمونه‌ای که نشان می‌دهد هسته بدون هیچ افزونه‌ی دیگری کار می‌کند:
دو ابزار فقط‌خواندنی (`list_my_notes`، `get_leave_balance`)، یک ابزار پیشنهاد (`propose_add_note` ⇒ اقدام معلق
`add_note`)، یک مسیر سریع («چند روز مرخصی دارم؟») و یک قطعه‌ی پرامپت. کد در `agent_helper_demo/plugin.py`.

پروژه‌ی مستقل (SQLite، فقط هسته و همین افزونه):
```bash
cd agent_helper_demo
python manage.py migrate
python manage.py test agent_helper agent_helper_demo
```
تنظیم اختیاری: `AGENT_HELPER_DEMO = {'YEARLY_LEAVE_DAYS': 26}`.

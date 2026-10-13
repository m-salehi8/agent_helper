# agent-helper-demo

> **Beta (0.1.0b1)** — not a stable release yet. [فارسی](README.fa.md)

An example "my notes" plugin for `agent_helper`, and proof that the core works without any other plugin:
two read-only tools (`list_my_notes`, `get_leave_balance`), one proposing tool (`propose_add_note` ⇒ pending action
`add_note`), one fast route ("how many leave days do I have?") and one prompt fragment. The code is in
`agent_helper_demo/plugin.py`.

Standalone project (SQLite, only the core and this plugin):
```bash
cd packages/agent_helper_demo
python manage.py migrate
python manage.py test agent_helper agent_helper_demo
```
Optional setting: `AGENT_HELPER_DEMO = {'YEARLY_LEAVE_DAYS': 26}`.

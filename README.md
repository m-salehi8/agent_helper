# agent-helper

[![status: beta](https://img.shields.io/badge/status-beta-orange)](agent_helper/agent_helper/docs/en/changelog.html)
![version](https://img.shields.io/badge/version-0.1.0b1-blue)

> **Beta (0.1.0b1)** — this is a pre-release, not a stable version yet. The API and settings may change before 1.0;
> install with `--pre` or pin the exact version. [فارسی](README.fa.md)

A pluggable assistant for Django: an LLM tool loop, a no-LLM fast path (regex + Jev or a local model), actions that run
only when the user presses the button, image attachments, full logging and SSE streaming. No default address points to
the internet, so it fits offline deployments with self-hosted models.

| Folder | Package | Role |
|---|---|---|
| [`agent_helper/`](agent_helper/README.md) | `agent-helper` | The generic core |
| [`agent_helper_demo/`](agent_helper_demo/README.md) | `agent-helper-demo` | Example "notes and leave" plugin + a standalone SQLite project |

Full documentation (HTML): `agent_helper/agent_helper/docs/en/index.html` (English) and
`agent_helper/agent_helper/docs/index.html` (Persian). Source in `agent_helper/docs_src/`
(`python agent_helper/docs_src/build.py`).

## Quick start
```bash
pip wheel --no-deps --no-build-isolation -w dist ./agent_helper ./agent_helper_demo
pip install --find-links dist --pre agent-helper agent-helper-demo

cd agent_helper_demo
python manage.py migrate
python manage.py test agent_helper agent_helper_demo
```

```python
# settings.py
INSTALLED_APPS += ['rest_framework', 'django_jalali', 'agent_helper', 'myplugin']
AGENT_HELPER = {'LLM_PROVIDER': 'openai', 'LLM_BASE_URL': 'http://llm.internal:8000/v1', 'LLM_MODEL': 'qwen3'}

# urls.py
path('api/assistant/', include('agent_helper.urls'))
```

Writing a plugin: the "Writing a plugin" page of the docs and `agent_helper_demo/agent_helper_demo/plugin.py`.

Requirements: Python ≥ 3.10, Django ≥ 4.2, djangorestframework, django-jalali, jdatetime, requests.

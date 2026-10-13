# agent-helper

دستیار هوشمند افزونه‌پذیر برای Django: حلقه‌ی LLM با ابزار، مسیر سریع بدون LLM (regex + Jev یا مدل لوکال)،
اقدام‌هایی که فقط با دکمه‌ی خود کاربر اجرا می‌شوند، پیوست تصویر، لاگ کامل و استریم SSE. هیچ نشانی پیش‌فرضی به اینترنت
اشاره نمی‌کند؛ مناسب استقرار آفلاین و مدل‌های خودمیزبان.

| پوشه | پکیج | نقش |
|---|---|---|
| [`agent_helper/`](agent_helper/README.md) | `agent-helper` | هسته‌ی عمومی |
| [`agent_helper_demo/`](agent_helper_demo/README.md) | `agent-helper-demo` | افزونه‌ی نمونه («یادداشت و مرخصی») + پروژه‌ی مستقل SQLite |

مستندات کامل (HTML): `agent_helper/agent_helper/docs/index.html` — منبع آن در `agent_helper/docs_src/` است
(`python agent_helper/docs_src/build.py`).

## شروع سریع
```bash
pip wheel --no-deps --no-build-isolation -w dist ./agent_helper ./agent_helper_demo
pip install --find-links dist agent-helper agent-helper-demo

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

نوشتن افزونه: صفحه‌ی «نوشتن افزونه» در مستندات و کد `agent_helper_demo/agent_helper_demo/plugin.py`.

نیازمندی‌ها: Python ≥ 3.10، Django ≥ 4.2، djangorestframework، django-jalali، jdatetime، requests.

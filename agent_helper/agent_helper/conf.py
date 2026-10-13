"""Settings of agent_helper.

Every key is resolved at call time in this order:
1. ``settings.AGENT_HELPER[key]`` if present;
2. the environment variable listed below;
3. the default.

No default points to an external service: LLM, Jev and vision endpoints must be configured with URLs
(the package is meant for offline, self-hosted deployments).
"""
import os
from typing import Any

from django.conf import settings

# key: (environment variable or None, default)
DEFAULTS = {
    # LLM (tool loop)
    'LLM_PROVIDER': ('ASSISTANT_LLM_PROVIDER', 'anthropic'),   # anthropic | openai (any OpenAI-compatible server)
    'LLM_BASE_URL': ('ASSISTANT_LLM_BASE_URL', ''),
    'LLM_API_KEY': ('ASSISTANT_LLM_API_KEY', ''),
    'LLM_MODEL': ('ASSISTANT_LLM_MODEL', ''),
    'LLM_TIMEOUT': ('ASSISTANT_LLM_TIMEOUT', 30),
    'MAX_AGENT_ITERATIONS': (None, 6),
    # fast route (no LLM)
    'USE_FAST_ROUTER': ('ASSISTANT_USE_FAST_ROUTER', ''),     # '1' = on
    'FAST_THRESHOLD': ('ASSISTANT_FAST_THRESHOLD', 0.8),
    'INTENT_BACKEND': ('ASSISTANT_INTENT_BACKEND', 'jev'),    # jev | llm (local model with logprobs)
    'INTENT_TIMEOUT': ('ASSISTANT_INTENT_TIMEOUT', 4.0),
    'INTENT_BASE_URL': ('ASSISTANT_INTENT_BASE_URL', ''),     # llm backend; default: LLM_BASE_URL
    'INTENT_API_KEY': ('ASSISTANT_INTENT_API_KEY', ''),
    'INTENT_MODEL': ('ASSISTANT_INTENT_MODEL', ''),
    'JEV_BASE_URL': ('TYPESAFE_BASE_URL', ''),
    'JEV_API_KEY': ('TYPESAFE_API_KEY', ''),
    'JEV_MODEL': ('TYPESAFE_MODEL', 'jev-1.13.0'),
    # image attachments
    'VISION_BASE_URL': ('ASSISTANT_VISION_BASE_URL', ''),     # default: LLM_BASE_URL
    'VISION_API_KEY': ('ASSISTANT_VISION_API_KEY', ''),
    'VISION_MODEL': ('ASSISTANT_VISION_MODEL', ''),
    'VISION_TIMEOUT': ('ASSISTANT_VISION_TIMEOUT', 90),
    'UPLOAD_DIR': (None, 'assistant_uploads'),
    'MAX_UPLOAD_BYTES': (None, 5 * 1024 * 1024),
    # limits
    'PER_MINUTE_LIMIT': (None, 30),
    'DAILY_LIMIT': (None, None),                               # None: settings.ASSISTANT_DAILY_LIMIT or 100
    'ACTION_EXPIRES_MINUTES': (None, 10),
    # LLM context size: 'auto' = only tools/prompt rules relevant to the message (all when unsure); 'all'
    'TOOL_SELECTION': ('ASSISTANT_TOOL_SELECTION', 'auto'),
    # admin
    'REGISTER_ADMIN': (None, True),
    'ADMIN_BASE': (None, 'django.contrib.admin.ModelAdmin'),
    'ADMIN_INLINE_BASE': (None, 'django.contrib.admin.TabularInline'),
    # prompt identity (a plugin may also provide an identity fragment)
    'ASSISTANT_TITLE': (None, None),
    'ASSISTANT_MISSION': (None, None),
    'TODAY_LINE': (None, True),
}


def get(key: str) -> Any:
    env_name, default = DEFAULTS[key]
    user_settings = getattr(settings, 'AGENT_HELPER', None) or {}
    if key in user_settings:
        return user_settings[key]
    if env_name and os.getenv(env_name) not in (None, ''):
        value = os.getenv(env_name)
        if isinstance(default, bool):
            return value.strip().lower() in ('1', 'true', 'yes', 'on')
        if isinstance(default, int) and not isinstance(default, bool):
            return int(float(value))
        if isinstance(default, float):
            return float(value)
        return value.strip()
    return default


def flag(key: str) -> bool:
    value = get(key)
    return value in (True, 1) or str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def daily_limit() -> int:
    value = get('DAILY_LIMIT')
    return value if value is not None else getattr(settings, 'ASSISTANT_DAILY_LIMIT', 100)

"""Helpers for tests of agent_helper and its plugins.

A host project whose user model needs extra setup in tests can point AGENT_HELPER['TEST_USER_FACTORY'] to a
``callable(username) -> user``.
"""
import contextlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string


def make_user(username: str):
    factory = (getattr(settings, 'AGENT_HELPER', None) or {}).get('TEST_USER_FACTORY')
    if factory:
        return import_string(factory)(username)
    return get_user_model().objects.create_user(username=username, password=None)


@contextlib.contextmanager
def fast_router(on: bool = True, **env):
    """Turn the fast route on/off (and set other env-based settings) for a block"""
    from unittest import mock
    values = {'ASSISTANT_USE_FAST_ROUTER': '1' if on else '0', **env}
    with mock.patch.dict('os.environ', values):
        yield

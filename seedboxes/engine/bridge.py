"""One engine identity and serialization gate shared by legacy/new generation."""
from functools import lru_cache, wraps
from importlib.metadata import distribution
import json
import platform
from threading import RLock

ENGINE_COMMIT = '9d93cd81b05d6ef5b0f3d4b4d6ed7eaf5bbed0dd'
ENGINE_LOCK = RLock()


@lru_cache(maxsize=1)
def engine_fingerprint() -> dict:
    dist = distribution('boxes')
    source = json.loads(dist.read_text('direct_url.json') or '{}')
    actual = source.get('vcs_info', {}).get('commit_id')
    if actual != ENGINE_COMMIT:
        raise ValueError('增强模式需要已锁定的 Boxes.py 提交；请使用 uv sync --locked')
    return {'name': 'boxes', 'version': dist.version, 'commit': actual,
            'pythonVersion': platform.python_version()}


def serialized_render(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with ENGINE_LOCK:
            return function(*args, **kwargs)
    return wrapped

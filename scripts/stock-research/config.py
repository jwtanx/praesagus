"""Validated local request budgets. Import and configuration perform no network I/O."""
from dataclasses import dataclass, fields
from pathlib import Path
import math
import tomllib


@dataclass(frozen=True)
class ProviderConfig:
    max_requests: int = 128
    max_pages: int = 16
    max_rows: int = 100000
    screen_limit: int = 300
    history_num: int = 370
    history_window_days: int = 180
    timeout_seconds: float = 10.0
    autype: int = 0

    def __post_init__(self):
        bounds = {'max_requests': (1, 2048), 'max_pages': (1, 64), 'max_rows': (1, 250000),
                  'screen_limit': (1, 300), 'history_num': (1, 370),
                  'history_window_days': (1, 180), 'autype': (0, 2)}
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError('invalid provider configuration: ' + name)
        if type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 30:
            raise ValueError('invalid provider configuration: timeout_seconds')


def load_config(path=None):
    """Only documented provider settings; no credential values belong in TOML."""
    if path is None:
        return ProviderConfig()
    value = tomllib.loads(Path(path).read_text())
    if set(value) != {'provider'} or not isinstance(value['provider'], dict):
        raise ValueError('configuration needs only provider settings')
    allowed = {field.name for field in fields(ProviderConfig)}
    if not set(value['provider']) <= allowed:
        raise ValueError('unknown provider setting')
    return ProviderConfig(**value['provider'])

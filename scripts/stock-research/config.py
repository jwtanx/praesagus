"""Validated local request budgets. Import and configuration perform no network I/O."""
from dataclasses import dataclass, fields, field
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
    autype: int = 1

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
    if not set(value) <= {'provider', 'collection'} or not isinstance(value.get('provider'), dict):
        raise ValueError('configuration needs only provider settings')
    allowed = {field.name for field in fields(ProviderConfig)}
    if not set(value['provider']) <= allowed:
        raise ValueError('unknown provider setting')
    return ProviderConfig(**value['provider'])


@dataclass(frozen=True)
class CollectionConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    state_parent: str = field(default_factory=lambda: str(Path.home() / 'Documents/stock-research-data'))
    metadata_file: str = ''
    credential_locator_file: str = ''
    calendar: str = 'XNYS'
    history_years: int = 3
    revision_sessions: int = 5
    discovery_pages: int = 1
    max_candidates: int = 900
    metadata_enabled: bool = False
    etf_directory_manifest: str = ''
    etf_directory_candidates_per_run: int = 40

    def __post_init__(self):
        if not isinstance(self.provider, ProviderConfig) or self.calendar != 'XNYS':
            raise ValueError('invalid collection calendar/provider')
        for name, high in [('history_years', 5), ('revision_sessions', 20), ('discovery_pages', self.provider.max_pages), ('max_candidates', 5000)]:
            if type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= high:
                raise ValueError('invalid collection configuration: ' + name)
        if type(self.metadata_enabled) is not bool or not isinstance(self.state_parent, str) or not self.state_parent or not isinstance(self.metadata_file, str) or not isinstance(self.credential_locator_file, str):
            raise ValueError('invalid collection paths/metadata option')
        if not isinstance(self.etf_directory_manifest, str) or type(self.etf_directory_candidates_per_run) is not int or not 1 <= self.etf_directory_candidates_per_run <= 400:
            raise ValueError('invalid ETF directory configuration')


def load_collection_config(path=None):
    if path is None:
        return CollectionConfig()
    value = tomllib.loads(Path(path).read_text())
    settings = value.get('collection', {})
    if not isinstance(settings, dict) or not set(settings) <= {f.name for f in fields(CollectionConfig)} - {'provider'}:
        raise ValueError('unknown collection setting')
    return CollectionConfig(provider=load_config(path), **settings)

"""Registry for available ingestion connectors."""

from .airtable import AirtableConnector
from .hackernews import HackerNewsConnector
from .reddit import RedditConnector
from .twitter import XConnector
from .tiktok import TikTokConnector
from .threads import ThreadsConnector


SUPPORTED_CONNECTORS = {
    "reddit": RedditConnector,
    "twitter": XConnector,
    "x": XConnector,
    "airtable": AirtableConnector,
    "hackernews": HackerNewsConnector,
    "tiktok": TikTokConnector,
    "threads": ThreadsConnector,
}


def get_connector(name: str, **kwargs):
    connector_cls = SUPPORTED_CONNECTORS.get(name.lower())
    if connector_cls is None:
        raise ValueError(f"Unsupported connector: {name}")
    return connector_cls(**kwargs)

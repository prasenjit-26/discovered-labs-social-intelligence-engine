from app.sources.content_base import ContentSourcePlugin
from app.sources.hackernews.algolia import HackerNewsAlgoliaSource


def get_hackernews_source() -> ContentSourcePlugin:
    return HackerNewsAlgoliaSource()

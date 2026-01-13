from app.sources.content_base import ContentSourcePlugin
from app.sources.x.chain import ChainXSource


def get_x_source() -> ContentSourcePlugin:
    return ChainXSource()

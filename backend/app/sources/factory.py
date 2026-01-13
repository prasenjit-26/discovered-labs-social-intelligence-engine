from app.sources.base import SocialSourcePlugin
from app.sources.reddit import RedditPlugin
from app.sources.fallback import FallbackRedditSource
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_reddit_source() -> SocialSourcePlugin:
    """
    Returns the appropriate Reddit source based on configuration.
    """
    if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
        logger.info("Using Real Reddit Plugin")
        return RedditPlugin()
    else:
        logger.warning("Using Fallback/Mock Reddit Source (Missing Credentials)")
        return FallbackRedditSource(dataset_path="app/sources/data/reddit_sample.json")

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Intelligence Engine"

    # Reddit API (We will need these later)
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "python:social-engine:v1.0 (by /u/discoveredlabs_candidate)"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"

    # X / Twitter (Level 3)
    X_BEARER_TOKEN: str = ""
    NITTER_BASE_URL: str = "https://nitter.net"
    NITTER_FALLBACK_URLS: str = "https://nitter.net,https://nitter.poast.org,https://nitter.privacydev.net"

    class Config:
        env_file = ".env"

settings = Settings()

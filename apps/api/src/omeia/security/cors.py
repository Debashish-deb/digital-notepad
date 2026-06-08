import os

def get_cors_origins() -> list[str]:
    """
    Parses CORS_ORIGINS strictly.
    Production must allow only exact frontend origins.
    """
    app_env = os.getenv("APP_ENV", "development").lower()
    raw_origins = os.getenv("CORS_ORIGINS", "")
    
    if app_env == "production":
        if not raw_origins or raw_origins == "*":
            raise RuntimeError("CORS_ORIGINS must be set to strict frontend origins in production.")
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        if "*" in origins:
            raise RuntimeError("CORS_ORIGINS cannot contain wildcard '*' in production.")
        return origins
    else:
        # In development, fallback to * if not specified
        if not raw_origins:
            return ["*"]
        return [o.strip() for o in raw_origins.split(",") if o.strip()]

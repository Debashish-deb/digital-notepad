import os

def validate_environment():
    """
    Validates security-critical environment variables at startup.
    Fails loudly (raises RuntimeError) if production config is unsafe.
    """
    app_env = os.getenv("APP_ENV", "development").lower()
    
    auth_disabled_str = os.getenv("PLATFORM_AUTH_DISABLED", "false").lower()
    auth_disabled = auth_disabled_str in ("1", "true", "yes")
    
    auth_skip_str = os.getenv("PLATFORM_AUTH_ALLOW_SKIP", "false").lower()
    auth_skip = auth_skip_str in ("1", "true", "yes")
    
    cors_origins = os.getenv("CORS_ORIGINS", "").strip()
    
    if app_env == "production":
        if auth_disabled:
            raise RuntimeError("CRITICAL SECURITY ERROR: PLATFORM_AUTH_DISABLED cannot be true in production.")
        
        if auth_skip:
            raise RuntimeError("CRITICAL SECURITY ERROR: PLATFORM_AUTH_ALLOW_SKIP cannot be true in production.")
            
        if not cors_origins or cors_origins == "*":
            raise RuntimeError("CRITICAL SECURITY ERROR: CORS_ORIGINS must be set to strict frontend origins (not '*') in production.")
            
        # Check Firebase credentials
        firebase_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
        if not firebase_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # A fallback checking if a raw dict env var is provided could be added here
            raise RuntimeError("CRITICAL SECURITY ERROR: Firebase credentials must be provided in production (FIREBASE_SERVICE_ACCOUNT_PATH or GOOGLE_APPLICATION_CREDENTIALS).")

import json
from functools import wraps
from fastapi import HTTPException

def load_flags():
    """Loads feature flags from a JSON file."""
    try:
        with open("feature_flags.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"indicators": {}}

feature_flags = load_flags()

def flag_enabled(flag_name: str):
    """Decorator to check if a feature flag is enabled for an endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if feature_flags.get("indicators", {}).get(flag_name, False):
                return await func(*args, **kwargs)
            else:
                raise HTTPException(status_code=404, detail=f"Indicator '{flag_name}' is not enabled.")
        return wrapper
    return decorator

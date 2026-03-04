import os

from fastapi import Header, HTTPException


def get_api_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


async def verify_api_key(x_api_key: str = Header(..., alias="X-Api-Key")) -> str:
    keys = get_api_keys()
    if not keys:
        # No keys configured — open access (development mode)
        return "dev"
    if x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

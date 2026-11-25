"""
forecast_store.py — keeps the latest 24h AI forecast that the hourly GitHub Action sends.

The heavy model never runs on Render. The Action posts its JSON to /api/forecast/ingest with a
GitHub OIDC token; we accept it only if GitHub signed it for THIS repo's forecast workflow on main.
No shared secret is needed. The latest forecast is kept in memory and in a small file so a
restart between runs still has something to show.
"""
from __future__ import annotations

import json
import os
import threading
import time


ISSUER = "https://token.actions.githubusercontent.com"
AUDIENCE = "cryptoai-forecast"
# This repo, by GitHub's numeric id (survives renames) or by its current name.
REPO_ID = os.environ.get("FORECAST_REPO_ID", "1431990166")
REPO_NAMES = {"siamak-pacar/cryptoai-main-site"}
WORKFLOW = "/.github/workflows/kronos-forecast.yml@refs/heads/main"
PATH = os.environ.get("FORECAST_FILE", "/tmp/cryptoai_forecast.json")
MAX_AGE_H = 6  # older than this is hidden from visitors

_jwks = None
_lock = threading.Lock()
_state = {"data": None, "received": 0.0, "last_error": None}


def _load():
    try:
        with open(PATH) as f:
            d = json.load(f)
        _state["data"], _state["received"] = d.get("data"), float(d.get("received", 0))
    except Exception:
        pass


_load()


def verify(auth_header: str) -> dict:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise PermissionError("missing token")
    import jwt  # PyJWT — imported here so a missing package can never stop the site from starting
    global _jwks
    if _jwks is None:
        _jwks = jwt.PyJWKClient(ISSUER + "/.well-known/jwks", cache_keys=True, lifespan=3600)
    token = auth_header.split(" ", 1)[1].strip()
    key = _jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER, leeway=60)
    repo = (claims.get("repository") or "").lower()
    if str(claims.get("repository_id")) != REPO_ID and repo not in REPO_NAMES:
        raise PermissionError("wrong repository")
    if (claims.get("workflow_ref") or "").lower() != f"{repo}{WORKFLOW}":
        raise PermissionError("wrong workflow")
    return claims


def _clean(payload: dict) -> dict:
    coins = {}
    for sym, c in (payload.get("coins") or {}).items():
        if not isinstance(c, dict) or sym not in ("BTC", "ETH", "SOL", "XRP"):
            continue
        nums = lambda a: [float(x) for x in (a or [])][:72]  # noqa: E731
        coins[sym] = {
            "last": float(c["last"]), "last_time": str(c.get("last_time", ""))[:25],
            "bias": c.get("bias") if c.get("bias") in ("up", "down", "flat") else "flat",
            "up_share": float(c.get("up_share", 0.5)), "chg_24h": float(c.get("chg_24h", 0)),
            "range_24h": nums(c.get("range_24h"))[:2],
            "history": nums(c.get("history")), "median": nums(c.get("median")),
            "p10": nums(c.get("p10")), "p90": nums(c.get("p90")),
        }
    if not coins:
        raise ValueError("no coins")
    return {"generated_at": str(payload.get("generated_at", ""))[:25], "horizon_h": int(payload.get("horizon_h", 24)),
            "coins": coins}


def ingest(auth_header: str, payload: dict) -> None:
    try:
        verify(auth_header)
        data = _clean(payload)
    except Exception as e:
        _state["last_error"] = f"{type(e).__name__}: {e}"[:200]
        raise
    with _lock:
        _state["data"], _state["received"], _state["last_error"] = data, time.time(), None
        try:
            with open(PATH, "w") as f:
                json.dump({"data": data, "received": _state["received"]}, f)
        except Exception:
            pass
    try:   # paid Pro Telegram channel gets the full picture (at most every few hours)
        import forecast_post
        forecast_post.maybe_post(data)
    except Exception:
        pass


def latest() -> dict | None:
    if not _state["data"] or time.time() - _state["received"] > MAX_AGE_H * 3600:
        return None
    return dict(_state["data"], age_min=int((time.time() - _state["received"]) / 60))


def status() -> dict:
    return {"has_data": bool(latest()), "age_min": int((time.time() - _state["received"]) / 60) if _state["received"] else None,
            "last_error": _state["last_error"]}

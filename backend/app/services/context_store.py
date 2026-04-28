# Compatibility shim — import from new location.
from app.services.stores.context_store import *  # noqa: F401,F403
from app.services.stores.context_store import _ensure_collection  # noqa: F401

import types
from importlib.metadata import PackageNotFoundError, version

from .database import DB
from .pool import close_cursor, close_pool, create_pool, get_cursor

try:
    __version__ = version("mypackage")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "DB",
    "__version__",
    "close_cursor",
    "close_pool",
    "create_pool",
    "get_cursor",
    "types"
]

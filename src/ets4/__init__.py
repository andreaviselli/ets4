"""ETS4 editorial review tooling."""

__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "get_ets4":
        from .legacy import get_ets4

        return get_ets4
    raise AttributeError(f"module 'ets4' has no attribute {name!r}")

# Backward-compat shim — import from the adapters package instead.
from promptops.core.adapters import ModelResponse, OllamaAdapter, BaseAdapter, make_adapter

__all__ = ["ModelResponse", "OllamaAdapter", "BaseAdapter", "make_adapter"]

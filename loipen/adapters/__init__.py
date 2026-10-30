"""Registry der Adapter. Neue Adapter werden hier eingetragen."""

from loipen.adapters.base import Adapter

ADAPTERS: dict[str, Adapter] = {}

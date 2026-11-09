"""Registry der Adapter. Neue Adapter werden hier eingetragen (P1)."""

from loipen.adapters.aschau import AschauAdapter
from loipen.adapters.ats import AtsAdapter
from loipen.adapters.base import Adapter

ADAPTERS: dict[str, Adapter] = {"ats": AtsAdapter(), "aschau": AschauAdapter()}

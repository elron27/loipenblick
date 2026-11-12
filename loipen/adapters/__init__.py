"""Registry der Adapter. Neue Adapter werden hier eingetragen (P1)."""

from loipen.adapters.aschau import AschauAdapter
from loipen.adapters.ats import AtsAdapter
from loipen.adapters.base import Adapter
from loipen.adapters.tirolat import TirolAtAdapter
from loipen.adapters.tourinfra import TourinfraAdapter

ADAPTERS: dict[str, Adapter] = {
    "ats": AtsAdapter(), "aschau": AschauAdapter(),
    "tourinfra": TourinfraAdapter(), "tirolat": TirolAtAdapter(),
}

"""Registry der Adapter. Neue Adapter werden hier eingetragen (P1)."""

from loipen.adapters.aschau import AschauAdapter
from loipen.adapters.ats import AtsAdapter
from loipen.adapters.base import Adapter
from loipen.adapters.kitzalps import KitzAlpsAdapter
from loipen.adapters.langlaufdorf import LanglaufdorfAdapter
from loipen.adapters.seefeld import SeefeldAdapter
from loipen.adapters.stammdaten import StammdatenAdapter
from loipen.adapters.suedtirol import DolomitiNordicSkiAdapter, OpenDataHubAdapter
from loipen.adapters.tirolat import TirolAtAdapter
from loipen.adapters.tourinfra import TourinfraAdapter
from loipen.adapters.tvb_tirol import AchenseeAdapter, KaiserwinklAdapter, SkidataAdapter

ADAPTERS: dict[str, Adapter] = {
    "ats": AtsAdapter(), "aschau": AschauAdapter(),
    "tourinfra": TourinfraAdapter(), "tirolat": TirolAtAdapter(),
    "langlaufdorf": LanglaufdorfAdapter(), "stammdaten": StammdatenAdapter(),
    "kitzalps": KitzAlpsAdapter(), "seefeld": SeefeldAdapter(),
    "achensee": AchenseeAdapter(), "skidata": SkidataAdapter(), "kaiserwinkl": KaiserwinklAdapter(),
    "dolomiti": DolomitiNordicSkiAdapter(), "opendatahub": OpenDataHubAdapter(),
}

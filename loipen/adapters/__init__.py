"""Registry der Adapter. Neue Adapter werden hier eingetragen (P1)."""

from loipen.adapters.aschau import AschauAdapter
from loipen.adapters.ats import AtsAdapter
from loipen.adapters.base import Adapter
from loipen.adapters.intermaps import IntermapsSchneeberichtAdapter
from loipen.adapters.kaernten import NlwBerichtAdapter
from loipen.adapters.kitzalps import KitzAlpsAdapter
from loipen.adapters.langlaufdorf import LanglaufdorfAdapter
from loipen.adapters.osttirol import OsttirolAdapter
from loipen.adapters.schweiz import MySwitzerlandAdapter
from loipen.adapters.seefeld import SeefeldAdapter
from loipen.adapters.stammdaten import StammdatenAdapter
from loipen.adapters.steiermark import SteiermarkLoipenberichtAdapter
from loipen.adapters.suedtirol import DolomitiNordicSkiAdapter, OpenDataHubAdapter
from loipen.adapters.tirolat import TirolAtAdapter
from loipen.adapters.tourinfra import TourinfraAdapter
from loipen.adapters.tvb_tabelle import TvbTabelleAdapter
from loipen.adapters.oetztal import OetztalAdapter
from loipen.adapters.paznaun import PaznaunAdapter
from loipen.adapters.pitztal import PitztalAdapter
from loipen.adapters.serfaus import SerfausAdapter
from loipen.adapters.tiroler_oberland import TirolerOberlandAdapter
from loipen.adapters.tvb_tirol import AchenseeAdapter, KaiserwinklAdapter, SkidataAdapter, StAntonAdapter
from loipen.adapters.wilderkaiser import WilderKaiserAdapter

ADAPTERS: dict[str, Adapter] = {
    "ats": AtsAdapter(), "aschau": AschauAdapter(),
    "tourinfra": TourinfraAdapter(), "tirolat": TirolAtAdapter(),
    "langlaufdorf": LanglaufdorfAdapter(), "stammdaten": StammdatenAdapter(),
    "kitzalps": KitzAlpsAdapter(), "seefeld": SeefeldAdapter(),
    "achensee": AchenseeAdapter(), "skidata": SkidataAdapter(), "kaiserwinkl": KaiserwinklAdapter(),
    "stanton": StAntonAdapter(), "nlw": NlwBerichtAdapter(),
    "dolomiti": DolomitiNordicSkiAdapter(), "opendatahub": OpenDataHubAdapter(),
    "myswitzerland": MySwitzerlandAdapter(), "steiermark": SteiermarkLoipenberichtAdapter(),
    "tvb_tabelle": TvbTabelleAdapter(), "wilderkaiser": WilderKaiserAdapter(),
    # P31: Tiroler Ortsseiten zur Querpruefung (E-24)
    "oetztal": OetztalAdapter(), "pitztal": PitztalAdapter(), "tiroler_oberland": TirolerOberlandAdapter(),
    "serfaus": SerfausAdapter(), "paznaun": PaznaunAdapter(),
    # P33: Osttirol, Zugspitz Arena (E-24)
    "osttirol": OsttirolAdapter(), "intermaps": IntermapsSchneeberichtAdapter(),
}

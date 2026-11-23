# Schneekarte: Quellen und Lizenzen

Erzeugt aus `config/schnee.yaml` mit `python -m loipen.schnee.doku`. Nicht von Hand ändern.
Grundlage: Prüfung vom 23.11.2026, Schnappschüsse und Lizenzseiten in `tests/fixtures/schnee-2026-11-23/`
(ausführlich in `quellen.md` dort).

**Einnahmen erlaubt** heißt: Die Lizenz erlaubt die Nutzung auch dann, wenn die Seite Spenden oder Affiliate-Links
hat. Bei *nein* oder *unklar* wird gesammelt, die Daten erscheinen aber nur in der Testversion (S6 AK 4), bis der
Betreiber zugestimmt hat. Open-Meteo ist nicht dabei (E-33).

| Quelle | Länder | Lizenz | Namensnennung | Einnahmen erlaubt | Erlaubnis | Archiv ab | Abruf (Uhr) |
|---|---|---|---|---|---|---|---|
| Lageberichte Bayern, Salzburg und weitere österreichische Länder (lawinen-warnung.eu) (`lawinen-warnung-eu`) | DE, AT, SI | [nicht angegeben; LWD Bayern verlangt Einwilligung, LWD Salzburg behält alle Rechte vor](https://lawinenwarndienst.bayern.de/impressum/) | Lawinenwarndienst Bayern, Lawinenwarndienst Salzburg und die jeweiligen Landeswarndienste | unklar | nur_test | 2024-12-01 | 8, 12, 18 |
| Lageberichte Tirol, Südtirol und Trentino (Euregio, avalanche.report) (`euregio`) | AT, IT | [nicht angegeben (Open-Data-Seite ist eine JavaScript-Anwendung); Tiroler OGD sonst CC BY 4.0](https://avalanche.report/more/open-data) | Lawinenwarndienst Tirol, Südtirol und Trentino (Euregio), avalanche.report | unklar | nur_test | 2018-12-04 | 8, 12, 18 |
| Lagebericht Kärnten (Lawinenwarndienst Kärnten) (`kaernten`) | AT | [CC BY 4.0](https://lawinenwarndienst.ktn.gv.at/info/opendata) | Daten bereitgestellt vom Lawinenwarndienst Kärnten, Amt der Kärntner Landesregierung | ja | liegt_vor | 2021-01-25 | 8, 12, 18 |
| Lawinenbulletin Schweiz (SLF) (`slf`) | CH | [CC BY 4.0](https://www.slf.ch/en/services-and-products/slf-data-service) | WSL-Institut für Schnee- und Lawinenforschung SLF, www.slf.ch | ja | liegt_vor | 2023-11-15 | 9, 12, 18 |
| Lageberichte italienische Alpen (AINEVA) (`aineva`) | IT | [nicht angegeben ("© Copyright Associazione interregionale")](https://www.aineva.it/) | AINEVA und die regionalen Lawinenwarndienste | unklar | nur_test | 2021-12-15 | 8, 12, 18 |
| Lageberichte Frankreich (Météo-France, über die EAWS-Sammlung) (`eaws-frankreich`) | FR | [nicht gefunden (Météo-France)](https://meteofrance.com/) | Météo-France, über avalanche.report | unklar | nur_test | 2021-12-01 | 8, 18 |
| EAWS-Sammlung früherer Lageberichte (avalanche.report) (`eaws-archiv`) | DE, AT, IT, SI, CH, FR | [wie der jeweilige Warndienst](https://static.avalanche.report/eaws_bulletins/) | die jeweiligen Lawinenwarndienste, über avalanche.report | unklar | nur_test | 2021-01-25 | nur von Hand (Archiv) |
| Warnregionen der Lawinenwarndienste (EAWS) (`eaws-regionen`) | DE, AT, IT, SI, CH, FR | [CC0 1.0](https://gitlab.com/eaws/eaws-regions/-/raw/master/LICENSE) | EAWS micro-regions (CC0) | ja | liegt_vor | – | 5 (montags) |
| Messstationen Lawinenwarndienst Bayern (`bayern-stationen`) | DE | [Weiterverwendung nur mit Einwilligung (Impressum)](https://lawinenwarndienst.bayern.de/impressum/) | Lawinenwarndienst Bayern | nein | nur_test | – | 7, 19 |
| DWD Tageswerte Bayerische Alpen (`dwd-klima`) | DE | [CC BY 4.0](https://opendata.dwd.de/climate_environment/CDC/Nutzungsbedingungen_German.txt) | Deutscher Wetterdienst | ja | liegt_vor | 1900-08-01 | 11 |
| Wetterstationen Tirol, Südtirol und Trentino (avalanche.report) (`euregio-stationen`) | AT, IT | [Tiroler Daten CC BY 4.0 (data.tirol.gv.at); für den Gesamtdatensatz nicht angegeben](https://www.tirol.gv.at/data/nutzungsbedingungen) | Datenquelle: Land Tirol - data.tirol.gv.at; Lawinenwarndienste Südtirol und Trentino | unklar | nur_test | 2026-11-17 | 7, 12, 18 |
| Messstationen Lawinenwarndienst Salzburg (`salzburg-stationen`) | AT | [Copyright Land Salzburg, sämtliche Rechte vorbehalten](https://lawine.salzburg.at/impressum) | Lawinenwarndienst Salzburg | nein | nur_test | – | 7, 12, 18 |
| Wetterstationen Südtirol (Wetterdienst der Provinz Bozen) (`suedtirol-stationen`) | IT | [CC0 1.0](https://data.civis.bz.it/de/dataset/misure-meteo-e-idrografiche) | Wetterdienst Südtirol, Autonome Provinz Bozen (CC0) | ja | liegt_vor | – | 7, 12, 18 |
| GeoSphere Austria Klima-Tageswerte (Stationen ab 700 m) (`geosphere-klima`) | AT | [CC BY 4.0](https://dataset.api.hub.geosphere.at/v1/docs/user-guide/license.html) | GeoSphere Austria (CC BY 4.0) | ja | liegt_vor | 1775-01-01 | 10 |
| GeoSphere SNOWGRID, modellierte Schneehöhe an den Loipengebieten in Österreich (`geosphere-snowgrid`) | AT | [CC BY 4.0](https://data.hub.geosphere.at/dataset/snowgrid_cl-v2-1d-1km) | GeoSphere Austria, SNOWGRID-CL (CC BY 4.0) | ja | liegt_vor | 1961-01-01 | 10 |
| ERA5-Land (Copernicus), Schneefall und Schneehöhe je Warnregion für den ganzen Alpenraum (`era5-land`) | DE, AT, IT, CH, FR, SI, LI | [CC BY 4.0](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview) | Generated using Copernicus Climate Change Service information [Jahr]. Muñoz Sabater, J. (2019): ERA5-Land hourly data from 1950 to present. C3S Climate Data Store, DOI 10.24381/cds.e2161bac | ja | liegt_vor | 1950-01-01 | 9 |
| IMIS-Stationen Schweiz (SLF) (`slf-stationen`) | CH | [CC BY 4.0](https://www.slf.ch/en/services-and-products/slf-data-service) | WSL-Institut für Schnee- und Lawinenforschung SLF, www.slf.ch | ja | liegt_vor | – | 9 |

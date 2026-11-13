"""App-Symbol als PNG ohne Zusatzpakete: Eisblau-Verlauf mit weisser Loipenspur (U8, U40).

rand > 0 ergibt das maskierbare Symbol fuer Android: Der Verlauf fuellt die ganze Flaeche, die Spuren
bleiben in der sicheren Mitte, damit runde oder tropfenfoermige Masken nichts abschneiden.
"""

import math
import struct
import zlib
from functools import lru_cache


@lru_cache(maxsize=8)
def png_icon(groesse: int, rand: float = 0.0) -> bytes:
    zeilen = bytearray()
    innen = 1 - 2 * rand
    for y in range(groesse):
        zeilen.append(0)
        v = y / groesse
        tv = (v - rand) / innen
        for x in range(groesse):
            u = x / groesse
            # Verlauf von Nachtblau nach Eisblau
            r, g, b = int(8 + 70 * v), int(40 + 150 * v * 0.9 + 20 * u), int(70 + 160 * v)
            tu = (u - rand) / innen
            if 0 <= tu <= 1:
                # zwei geschwungene Spuren
                for versatz in (0.0, 0.1):
                    mitte = 0.62 - 0.28 * math.sin((tu + versatz) * 3.1) + versatz
                    if abs(tv - mitte) < 0.028 / innen * (1 if rand == 0 else 1.6):
                        r, g, b = 255, 255, 255
            zeilen += bytes((r, g, b))

    def chunk(art: bytes, daten: bytes) -> bytes:
        c = struct.pack(">I", len(daten)) + art + daten
        return c + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)

    kopf = struct.pack(">IIBBBBB", groesse, groesse, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", kopf) + chunk(b"IDAT", zlib.compress(bytes(zeilen), 9)) + chunk(b"IEND", b"")

"""App-Symbol als PNG ohne Zusatzpakete: Eisblau-Verlauf mit weisser Loipenspur (U8)."""

import struct
import zlib


def png_icon(groesse: int) -> bytes:
    zeilen = bytearray()
    for y in range(groesse):
        zeilen.append(0)
        for x in range(groesse):
            u, v = x / groesse, y / groesse
            # Verlauf von Nachtblau nach Eisblau
            r, g, b = int(8 + 70 * v), int(40 + 150 * v * 0.9 + 20 * u), int(70 + 160 * v)
            # zwei geschwungene Spuren
            for versatz in (0.0, 0.1):
                mitte = 0.62 - 0.28 * __import__("math").sin((u + versatz) * 3.1) + versatz
                if abs(v - mitte) < 0.028:
                    r, g, b = 255, 255, 255
            zeilen += bytes((r, g, b))

    def chunk(art: bytes, daten: bytes) -> bytes:
        c = struct.pack(">I", len(daten)) + art + daten
        return c + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)

    kopf = struct.pack(">IIBBBBB", groesse, groesse, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", kopf) + chunk(b"IDAT", zlib.compress(bytes(zeilen), 9)) + chunk(b"IEND", b"")

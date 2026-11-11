"""Teststack ohne NAS starten, pruefen und wieder abbauen (docs/testumgebung.md).

    python scripts/teststack.py             bauen, starten, Stack-Tests, abbauen
    python scripts/teststack.py --behalten  Stack danach laufen lassen (Vorschau: http://localhost:18080)
    python scripts/teststack.py --ohne-bau  vorhandenes Image nutzen
    python scripts/teststack.py --abbauen   nur abbauen

Braucht Docker mit Compose v2.24 oder neuer und Python mit den Paketen aus requirements-dev.txt.
Funktioniert unter Linux, macOS und Windows. Ergebnisse unter .teststack/ (Seite, Dumps, Fotos, Logs).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.test.yml",
           "--env-file", "tests/stack/stack.env"]


def compose(*args: str, check: bool = True) -> int:
    print("+", " ".join(["docker compose", *args]), flush=True)
    return subprocess.run([*COMPOSE, *args], cwd=ROOT, check=check).returncode


def abbauen() -> None:
    compose("down", "-v", "--remove-orphans", check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behalten", action="store_true", help="Stack nach den Tests nicht abbauen")
    ap.add_argument("--ohne-bau", action="store_true", help="Image nicht neu bauen")
    ap.add_argument("--abbauen", action="store_true", help="nur abbauen")
    ap.add_argument("pytest_args", nargs="*", help="weitere Argumente fuer pytest")
    args = ap.parse_args()

    if args.abbauen:
        abbauen()
        return 0

    abbauen()  # immer mit leerer Datenbank beginnen, wie beim ersten Start auf dem NAS
    ausgabe = ROOT / ".teststack"
    if ausgabe.exists():
        shutil.rmtree(ausgabe, ignore_errors=True)
    (ausgabe / "logs").mkdir(parents=True, exist_ok=True)

    code = 1
    try:
        compose("up", "-d", "--wait", "--wait-timeout", "300", *([] if args.ohne_bau else ["--build"]))
        env = {**os.environ, "LOIPEN_TESTSTACK": "1"}
        code = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/stack",
                               "--junitxml=.teststack/junit-stack.xml", "-o", "junit_family=xunit1",
                               *args.pytest_args], cwd=ROOT, env=env).returncode
    finally:
        with open(ausgabe / "logs" / "compose.log", "w", encoding="utf-8") as f:
            subprocess.run([*COMPOSE, "logs", "--no-color", "--timestamps"], cwd=ROOT, stdout=f,
                           stderr=subprocess.STDOUT)
        if args.behalten:
            print("Stack laeuft weiter. Vorschau: http://localhost:18080  ntfy: http://localhost:18098/loipenblick-test"
                  "\nAbbauen: python scripts/teststack.py --abbauen")
        else:
            abbauen()
    return code


if __name__ == "__main__":
    sys.exit(main())

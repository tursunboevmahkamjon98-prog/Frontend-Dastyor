import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import get_settings

PG_DUMP = r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def parse_url(url: str) -> dict:
    m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)", url)
    if not m:
        raise SystemExit(f"DATABASE_URL tanilmadi: {url[:40]}...")
    user, password, host, port, name = m.groups()
    return {"user": user, "password": password, "host": host, "port": port, "name": name}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=0,
                    help="how many recent backups to keep (0 = keep all)")
    args = ap.parse_args()

    if not os.path.exists(PG_DUMP):
        raise SystemExit(f"pg_dump topilmadi: {PG_DUMP}")

    db = parse_url(get_settings().DATABASE_URL)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = os.path.join(BACKUP_DIR, f"dastyor_{stamp}.sql")

    env = dict(os.environ, PGPASSWORD=db["password"])
    cmd = [PG_DUMP, "-h", db["host"], "-p", db["port"], "-U", db["user"],
           "-d", db["name"], "--clean", "--if-exists", "--no-owner",
           "-f", out]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("pg_dump xatosi:\n" + (r.stderr or "")[-800:])

    size = os.path.getsize(out) / 1e6
    print(f"Zaxira: {out}  ({size:.1f} MB)")

    if args.keep:
        files = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql"))
        for old in files[:-args.keep]:
            os.remove(os.path.join(BACKUP_DIR, old))
            print("o'chirildi (eski):", old)


if __name__ == "__main__":
    main()

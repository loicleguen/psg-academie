#!/usr/bin/env python3
# backend/scripts/backfill_session_date.py
import os
from datetime import datetime, timedelta
from dateutil.parser import parse
from sqlalchemy import create_engine, text

DB_USER = os.getenv("POSTGRES_USER", "psguser")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "psgpass")
DB_NAME = os.getenv("POSTGRES_DB", "psgdb")
DB_HOST = os.getenv("DATABASE_HOST", os.getenv("DB_HOST", "db"))
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}", future=True)

def parse_mixed_date(s):
    s = (s or "").strip()
    if not s:
        return None
    # Excel serial number heuristic
    if s.isdigit():
        try:
            n = int(s)
            if 20000 < n < 60000:
                return datetime(1899, 12, 30) + timedelta(days=n)
        except Exception:
            pass
    # robust textual parsing (dayfirst)
    try:
        return parse(s, dayfirst=True, fuzzy=True)
    except Exception:
        return None

def main():
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, date FROM catapultsession")).all()
        updates = []
        for row in rows:
            sid, raw = row
            dt = parse_mixed_date(raw)
            if dt:
                updates.append((sid, dt.date()))
        print(f"Found {len(rows)} rows, will update {len(updates)} rows")
        for sid, d in updates:
            conn.execute(text("UPDATE catapultsession SET session_date = :d WHERE id = :id"), {"d": d, "id": sid})
    print("Backfill complete")

if __name__ == '__main__':
    main()

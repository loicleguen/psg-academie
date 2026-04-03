# ARCHIVE: references legacy `player` table which has been dropped.
# Keep for history; do not run without modification.

# /app/scripts/link_players_users.py
"""
Script de liaison Player -> User
Usage dans le conteneur :
    docker compose exec backend python /app/scripts/link_players_users.py

Usage local (si Postgres exposé et venv correct) :
    PYTHONPATH=backend python backend/scripts/link_players_users.py
"""

import os
import sys
import re
from sqlmodel import select

# ---- Ensure project root is on sys.path so `import src.*` works ----
# If this script is at /app/scripts, parent dir is /app which contains `src/`
THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(THIS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -----------------------------------------------------------------

from src.db.database import get_session
from src.models.player import Player
from src.models.user import User
from src.services.auth import AuthService


def _normalize(s: str) -> str:
    s2 = re.sub(r'[^a-z0-9]', '', (s or "").lower())
    return s2 or "user"


def main():
    created = 0
    linked = 0

    with get_session() as session:
        players = session.exec(select(Player)).all()

        for p in players:
            name = (p.name or "").strip()
            if not name:
                continue

            parts = re.split(r"\s+", name)
            first = parts[0] if parts else "player"
            last = parts[-1] if len(parts) > 1 else first
            email = f"{_normalize(first)}.{_normalize(last)}@import.local"

            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                try:
                    hashed = AuthService.get_password_hash(first)
                except Exception as e:
                    print("hash error for", name, ":", e)
                    continue

                user = User(email=email, hashed_password=hashed, full_name=name, role="player")
                session.add(user)
                session.flush()
                session.refresh(user)
                created += 1

            # lier si nécessaire
            if p.user_id != user.id:
                p.user_id = user.id
                session.add(p)
                linked += 1

        session.commit()

    print("users_created:", created, "players_linked:", linked)


if __name__ == "__main__":
    main()
    
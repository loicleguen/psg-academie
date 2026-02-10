# ARCHIVE: references legacy `player` table which has been dropped.
# Keep for history; do not run without modification.

# scripts/backfill_players_to_users.py
from sqlmodel import Session, select
from sqlalchemy import text
from src.db.database import engine
from src.models.player import Player
from src.models.user import User
from src.services.auth import AuthService

def backfill():
    with Session(engine) as session:
        mapping = {}  # player.id -> user.id
        players = session.exec(select(Player)).all()
        for p in players:
            fullname = (p.name or getattr(p, "player_name", "") or "").strip()
            # deterministic email
            parts = fullname.split()
            first = parts[0] if parts else "player"
            last = parts[-1] if len(parts) > 1 else first
            safe = lambda s: ''.join(ch for ch in s.lower() if ch.isalnum()) or 'user'
            email = f"{safe(first)}.{safe(last)}@import.local"

            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=AuthService.get_password_hash(first),
                    full_name=fullname or email,
                    role="player",
                    player_name=fullname,
                    team_id=p.team_id
                )
                session.add(user)
                session.flush()
                session.refresh(user)
            else:
                changed = False
                if not getattr(user, "player_name", None) and fullname:
                    user.player_name = fullname
                    changed = True
                if not getattr(user, "team_id", None) and getattr(p, "team_id", None):
                    user.team_id = p.team_id
                    changed = True
                if changed:
                    session.add(user)

            mapping[p.id] = user.id

        # update catapult sessions: set user_id where player_id present
        for player_id, user_id in mapping.items():
            session.execute(
                text("UPDATE catapultsession SET user_id = :uid WHERE player_id = :pid"),
                {"uid": user_id, "pid": player_id}
            )

        session.commit()
        print("Backfill done. Mapped", len(mapping), "players.")

if __name__ == "__main__":
    backfill()
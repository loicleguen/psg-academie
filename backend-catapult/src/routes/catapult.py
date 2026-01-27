from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ..models.user import User
from ..models.player import Player
from ..middleware.security import require_coach_or_admin
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List, Dict, Any
import pandas as pd
import base64
from fastapi import Query
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser
import re
from ..services.auth import AuthService

from ..db.database import get_session
from ..models.catapult import CatapultSession, CatapultSessionCreate
from ..services.catapult_parser import CatapultCSVParser
from ..services.split_detector import SplitDetector
from ..services.graph_generator import CatapultGraphGenerator
from ..services.report_generator import SessionReportGenerator

router = APIRouter(prefix="/catapult", tags=["Catapult GPS Data"])

def _parse_mixed_date(val):
    if val is None or val == "":
        return None
    s = str(val).strip()
    # Heuristique pour numéros Excel -> date (partie entière)
    try:
        f = float(s)
        if f > 59:
            serial = int(f)
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=serial)).date()
    except Exception:
        pass
    # Parsing robuste de texte
    try:
        return dateutil_parser.parse(s, dayfirst=True).date()
    except Exception:
        try:
            return pd.to_datetime(s, dayfirst=True).date()
        except Exception:
            return None


@router.post("/upload", response_model=Dict[str, Any])
async def upload_catapult_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Upload and process a Catapult CSV file
    
    - Parses the CSV
    - Stores data in database (creates User + Player when missing)
    - Returns summary statistics
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    content = await file.read()
    csv_content = content.decode('utf-8')
    
    # Parse CSV
    try:
        parsed_data = CatapultCSVParser.parse_csv(csv_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")
    
    if not parsed_data:
        raise HTTPException(status_code=400, detail="No data found in CSV")
    
    # Create missing Users and Players (force team_id = 13)
    for data in parsed_data:
        player_fullname = data.get("player_name", "").strip()
        if not player_fullname:
            continue

        # Normaliser le nom complet
        normalized = player_fullname.strip()

        # --- 1) Toujours tenter de créer un User (si absent) ---
        parts = re.split(r"\s+", player_fullname.strip())
        first = parts[0] if parts else "player"
        last = parts[-1] if len(parts) > 1 else first

        def _normalize(s: str) -> str:
            s2 = re.sub(r'[^a-z0-9]', '', s.lower())
            return s2 or "user"

        safe_first = _normalize(first)
        safe_last = _normalize(last)

        # construire email prenom.nom@import.local
        email = f"{safe_first}.{safe_last}@import.local"

        # créer le User uniquement si l'email n'existe pas (ne PAS écraser)
        user_exists = session.exec(select(User).where(User.email == email)).first()
        if not user_exists:
            try:
                hashed = AuthService.get_password_hash(first)
                db_user = User(email=email, hashed_password=hashed, full_name=player_fullname, role="player")
                session.add(db_user)
                session.flush()
                session.refresh(db_user)
            except Exception:
                # ne pas bloquer l'import si le hash ou la création échoue
                session.rollback()
                session.begin()

        # --- 2) Ensuite créer le Player seulement si absent ---
        existing = session.exec(
            select(Player).where(
                func.lower(Player.name) == normalized.lower(),
                Player.team_id == 13
            )
        ).first()
        if existing:
            continue

        player = Player(
            name=player_fullname,
            team_id=13,
            age=None
        )
        session.add(player)
        session.flush()
        session.refresh(player)
        
    # commit des Users/Players créés
    session.commit()

    # Store Catapult sessions (ensure session_date is provided)
    stored_sessions = []
    for data in parsed_data:
        parsed_date = _parse_mixed_date(data.get("date"))
        session_date = parsed_date or datetime.utcnow().date()

        try:
            session_create = CatapultSessionCreate(**data)
            payload = session_create.model_dump()
        except Exception:
            allowed = set(CatapultSessionCreate.__annotations__.keys())
            payload = {k: v for k, v in data.items() if k in allowed}

        db_session = CatapultSession(**payload, session_date=session_date)
        session.add(db_session)
        stored_sessions.append(db_session)

    session.commit()
    
    # Generate summary
    summary = CatapultCSVParser.get_session_summary(parsed_data)
    summary["records_stored"] = len(stored_sessions)
    summary["filename"] = file.filename
    
    return summary


@router.get("/sessions", response_model=List[str])
def get_sessions(db: Session = Depends(get_session)):
    # Return unique session titles ordered by the most recent session_date per title
    stmt = select(CatapultSession.session_title).group_by(CatapultSession.session_title).order_by(desc(func.max(CatapultSession.session_date)))
    rows = db.execute(stmt).all()
    return [r[0] for r in rows]


@router.get("/sessions/title")
def get_sessions_by_title(session_title: str, session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Get all sessions with a specific title"""
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    sessions = session.exec(statement).all()
    return sessions


@router.get("/sessions/player/{player_name}")
def get_player_sessions(player_name: str, session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Get all sessions for a specific player"""
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    sessions = session.exec(statement).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=CatapultSession)
def get_session_by_id(session_id: int, session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Get a specific Catapult training session by ID"""
    db_session = session.get(CatapultSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


@router.delete("/sessions/title")
def delete_sessions_by_title(
    session_title: str = Query(..., description="Session title to delete"),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Delete all sessions with a specific title"""
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    
    count = len(db_sessions)
    for db_session in db_sessions:
        session.delete(db_session)
    
    session.commit()
    
    return {"message": f"Deleted {count} sessions"}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Delete a Catapult session"""
    db_session = session.get(CatapultSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.delete(db_session)
    session.commit()
    
    return {"message": "Session deleted successfully"}


# ============================================================================
# SESSION REPORTS - Professional training reports
# ============================================================================

@router.post("/reports/session")
def generate_session_report(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Generate complete professional session report
    
    Automatically extracts:
    - Date from CSV data
    - Week number from date
    - Match/Training info from tags
    
    Includes:
    - Header with session info
    - 4 semi-circular gauges (Distance, HSR, DEC, Power Play)
    - Player performance table with color coding
    
    Args:
        session_title: Title of the session
    
    Returns:
        JSON with base64-encoded PNG image
    """
    # Get session data
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all sessions for benchmarks
    all_sessions_db = session.exec(select(CatapultSession)).all()
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    all_sessions_data = [s.model_dump() for s in all_sessions_db]
    
    # Generate report (metadata extracted automatically)
    img_base64 = SessionReportGenerator.generate_session_report(
        session_data=session_data,
        all_sessions=all_sessions_data,
        session_title=session_title
    )
    
    return {
        "session_title": session_title,
        "total_players": len(session_data),
        "report_image": img_base64,
        "format": "base64_png"
    }


@router.get("/reports/session.png")
def get_session_report_image(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Get session report as PNG image (directly viewable in browser)
    
    Automatically extracts date, week, and match info from session data
    
    Args:
        session_title: Title of the session
    
    Returns:
        PNG image
    """
    # Get session data
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all sessions for benchmarks
    all_sessions_db = session.exec(select(CatapultSession)).all()
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    all_sessions_data = [s.model_dump() for s in all_sessions_db]
    
    # Generate report (metadata extracted automatically)
    img_base64 = SessionReportGenerator.generate_session_report(
        session_data=session_data,
        all_sessions=all_sessions_data,
        session_title=session_title
    )
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")

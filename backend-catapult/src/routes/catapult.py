import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ..models.user import User
from ..models.team import Team
from ..middleware.security import require_coach_or_admin, get_current_user
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List, Dict, Any
import pandas as pd
import base64
from fastapi import Query, Body
from sqlalchemy import func, desc, distinct
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

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
import base64

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
    - Stores data in database (creates/updates User when missing)
    - Links sessions to users via `user_id`
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
    
    # Map normalized player name -> user.id (pour lier les sessions)
    name_to_user_id: dict[str, int] = {}

    # Créer / mettre à jour les Users importés (utilise la fonction utilitaire)
    from ..services.catapult_parser import create_or_update_users
    name_to_user_id = create_or_update_users(session, parsed_data, default_team_id=3)

    # commit des Users créés / modifiés
    session.commit()

    # Store Catapult sessions
    stored_sessions = []
    for data in parsed_data:
        parsed_date = _parse_mixed_date(data.get("date"))
        # Build session_date from title when possible (day+month from title, year from raw date)
        session_date = _construct_session_date_from_title(data.get("session_title"), data.get("date")) or parsed_date or datetime.utcnow().date()

        try:
            session_create = CatapultSessionCreate(**data)
            payload = session_create.model_dump()
        except Exception:
            allowed = set(CatapultSessionCreate.__annotations__.keys())
            payload = {k: v for k, v in data.items() if k in allowed}

        # normaliser le nom dans la ligne pour lookup
        player_name_in_row = (data.get("player_name") or "").strip()
        normalized_row = re.sub(r'\s+', ' ', player_name_in_row).strip().lower()
        uid = name_to_user_id.get(normalized_row)
        if uid:
            payload["user_id"] = uid

        # éviter conflit legacy
        payload.pop("player_id", None)

        db_session = CatapultSession(**payload, session_date=session_date)
        session.add(db_session)
        stored_sessions.append(db_session)

    session.commit()

    summary = CatapultCSVParser.get_session_summary(parsed_data)
    summary["records_stored"] = len(stored_sessions)
    summary["filename"] = file.filename

    return summary


@router.get("/sessions")
def get_sessions(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
) -> List[Dict[str, Any]]:
    """Get list of unique sessions with their counts"""
    # Group by session_title and get count of players, plus team_id from User table
    stmt = select(
        CatapultSession.session_title,
        func.max(CatapultSession.session_date).label('session_date'),
        func.max(CatapultSession.date).label('date'),
        func.count(func.distinct(CatapultSession.user_id)).label('player_count'),
        func.max(User.team_id).label('team_id')
    ).join(User, CatapultSession.user_id == User.id).group_by(CatapultSession.session_title).order_by(desc(func.max(CatapultSession.session_date)))
    
    results = session.exec(stmt).all()
    
    # Calculate week and year for each session
    result_list = []
    for r in results:
        # Parse the date to get ISO week number
        try:
            session_date = datetime.strptime(r.date, '%Y-%m-%d')
            iso_week = session_date.isocalendar()[1]
            iso_year = session_date.year
        except:
            iso_week = None
            iso_year = None
        
        result_list.append({
            'session_title': r.session_title,
            'session_date': r.session_date.isoformat() if hasattr(r.session_date, 'isoformat') else str(r.session_date) if r.session_date else None,
            'date': r.date,
            'player_count': r.player_count,
            'team_id': r.team_id,
            'week': iso_week,
            'year': iso_year
        })
    
    return result_list


@router.get("/sessions/title")
def get_sessions_by_title(session_title: str, session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Get all sessions with a specific title"""
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    sessions = session.exec(statement).all()
    return sessions



@router.get("/sessions/{session_title}/players")
def get_session_players(
    session_title: str,
    session: Session = Depends(get_session),
        current_user: User = Depends(require_coach_or_admin)
) -> List[str]:
    """Get list of unique player names for a specific session"""
    stmt = select(
        User.player_name
    ).join(
        CatapultSession, CatapultSession.user_id == User.id
    ).where(
        CatapultSession.session_title == session_title,
        CatapultSession.split_name == "all"
    ).distinct()
    
    results = session.exec(stmt).all()
    return sorted([r for r in results if r])


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
    """Delete a Catapult session by ID"""
    db_session = session.get(CatapultSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.delete(db_session)
    session.commit()
    
    return {"message": "Session deleted successfully"}


@router.delete("/sessions/by-title/{session_title:path}")
def delete_session_by_title(
    session_title: str,
    current_user: User = Depends(require_coach_or_admin),
    db: Session = Depends(get_session)
):
    """Delete all records for a session by title"""
    logger = logging.getLogger(__name__)
    logger.info(f"DELETE request received for session_title: {session_title}")
    logger.info(f"Current user: {current_user.email}, role: {current_user.role}")
    
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    sessions = db.exec(statement).all()
    
    logger.info(f"Found {len(sessions)} sessions to delete")
    
    if not sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    for db_session in sessions:
        db.delete(db_session)
    
    db.commit()
    
    logger.info(f"Successfully deleted {len(sessions)} sessions")
    return {"message": f"Session '{session_title}' deleted successfully", "deleted_count": len(sessions)}


# ============================================================================
# SESSION REPORTS - Professional training reports
# ============================================================================

def _construct_session_date_from_title(title: str, raw_date: str):
    """Extract day/month from title and year from raw_date (or fallback).
    Returns a `date` or None.
    """
    from datetime import date as _date
    if not title:
        return None
    right = title.split('/')[-1].strip()
    parts = __import__('re').split(r"\s+", right)
    day = None
    month = None
    for i,tok in enumerate(parts):
        if tok.isdigit() and 1 <= len(tok) <= 2:
            try:
                day = int(tok)
            except Exception:
                day = None
            if i+1 < len(parts):
                mtok = __import__('re').sub(r"[^a-zA-Zà-ÿÀ-Ÿéèêûîç'-]", "", parts[i+1]).lower()
                month = { 'janvier':1,'janv':1,'jan':1,'fevrier':2,'février':2,'fev':2,'fév':2,'mars':3,'mar':3,'avril':4,'avr':4,'mai':5,'may':5,'juin':6,'juillet':7,'juil':7,'aout':8,'août':8,'aou':8,'septembre':9,'sept':9,'sep':9,'octobre':10,'oct':10,'novembre':11,'nov':11,'decembre':12,'décembre':12,'dec':12,'déc':12 }.get(mtok)
            break
    if day and month:
        # year from raw_date
        y = None
        import re as _re
        if raw_date:
            m = _re.search(r"(\d{4})", str(raw_date))
            if m:
                try:
                    y = int(m.group(1))
                except Exception:
                    y = None
        if not y:
            y = _date.today().year
        try:
            return _date(y, month, day)
        except Exception:
            return None
    return None



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

    # Determine if CSV contains per-player splits (non-'all') — trust client splits if present
    # Keep all sessions with 'all' split, plus any specific splits
    # Only filter out 'all' if ALL players have specific splits
    split_names = set((row.get('split_name') or '').lower() for row in session_data)
    all_count = sum(1 for row in session_data if (row.get('split_name') or '').lower() == 'all')
    non_all_count = len(session_data) - all_count
    
    if all_count == 0 and non_all_count > 0:
        # No 'all' splits, only specific splits - use them all
        relevant = session_data
    elif all_count > 0:
        # We have 'all' splits - use them (most reliable)
        relevant = [r for r in session_data if (r.get('split_name') or '').lower() == 'all']
    else:
        # Fallback
        relevant = session_data

    all_sessions_data = [s.model_dump() for s in all_sessions_db]
    
    img_base64 = SessionReportGenerator.generate_session_report(
        session_data=relevant,
        all_sessions=all_sessions_data,
        session_title=session_title,
        raw_rows=session_data
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

    # Determine if CSV contains per-player splits (non-'all') — trust client splits if present
    # Keep all sessions with 'all' split, plus any specific splits
    # Only filter out 'all' if ALL players have specific splits
    split_names = set((row.get('split_name') or '').lower() for row in session_data)
    all_count = sum(1 for row in session_data if (row.get('split_name') or '').lower() == 'all')
    non_all_count = len(session_data) - all_count
    
    if all_count == 0 and non_all_count > 0:
        # No 'all' splits, only specific splits - use them all
        relevant = session_data
    elif all_count > 0:
        # We have 'all' splits - use them (most reliable)
        relevant = [r for r in session_data if (r.get('split_name') or '').lower() == 'all']
    else:
        # Fallback
        relevant = session_data

    all_sessions_data = [s.model_dump() for s in all_sessions_db]
    
    # Generate report (metadata extracted automatically)
    # Prefer player-specific splits if present (client-side crops).
    from ..services.split_detector import SplitDetector

    has_non_all = any((s.get('split_name') or '').lower() != 'all' for s in session_data)
    if has_non_all:
        relevant = [s for s in session_data if (s.get('split_name') or '').lower() != 'all']
    else:
        # Automatic filtering: keep only splits that look like real effort
        relevant = [s for s in session_data if SplitDetector.is_real_effort(s)]
        if not relevant:
            # fallback to aggregated 'all' split
            relevant = [s for s in session_data if (s.get('split_name') or '').lower() == 'all']
        if not relevant:
            relevant = session_data

    img_base64 = SessionReportGenerator.generate_session_report(
        session_data=relevant,
        all_sessions=all_sessions_data,
        session_title=session_title,
        raw_rows=session_data
    )
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


@router.get("/reports/weekly.png", tags=["Reports"])
def generate_weekly_report(
    team_id: int,
    week: int,
    year: int = 2026,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Générer un rapport hebdomadaire pour une équipe et une semaine donnée.
    """
    from datetime import datetime, timedelta
    from ..services.report_generator import WeeklyReportGenerator
    import base64
    
    # Calculer les dates de début et fin de la semaine
    jan_4 = datetime(year, 1, 4)
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    target_monday = week_1_monday + timedelta(weeks=week - 1)
    target_sunday = target_monday + timedelta(days=6)
    
    # Récupérer toutes les sessions de l'équipe
    stmt = select(CatapultSession).join(
        User, CatapultSession.user_id == User.id
    ).where(
        User.team_id == team_id,
        CatapultSession.split_name == "all"
    )
    
    all_sessions = session.exec(stmt).all()
    
    # Filtrer par date en Python (YYYY-MM-DD format)
    sessions = []
    for s in all_sessions:
        try:
            session_date = datetime.strptime(s.date, '%Y-%m-%d')
            if target_monday <= session_date <= target_sunday and s.split_name == "all":
                sessions.append(s)
        except (ValueError, AttributeError, TypeError):
            continue
    
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this week")
    
    # Récupérer le nom de l'équipe
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Convertir en dictionnaires
    session_data = [s.model_dump() for s in sessions]
    all_sessions_data = [s.model_dump() for s in all_sessions]
    
    # Générer le rapport
    img_base64 = WeeklyReportGenerator.generate_weekly_report(
        session_data=session_data,
        all_sessions=all_sessions_data,
        team_name=team.name,
        week_number=week,
        year=year
    )
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


# Code à ajouter dans backend-catapult/src/routes/catapult.py après l'endpoint weekly report

@router.get("/reports/individual-week.png", tags=["Reports"])
def generate_individual_week_report(
    player_name: str,
    week: int,
    year: int = 2026,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Generate individual player weekly microcycle report.
    """
    from datetime import datetime, timedelta
    from ..services.report_generator import IndividualWeekReportGenerator
    import base64
    
    # Calculate week dates
    jan_4 = datetime(year, 1, 4)
    week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
    target_monday = week_1_monday + timedelta(weeks=week - 1)
    target_sunday = target_monday + timedelta(days=6)
    
    week_start = target_monday.strftime('%d/%m/%Y')
    week_end = target_sunday.strftime('%d/%m/%Y')
    
    # Get player info
    stmt_user = select(User).where(
        func.lower(User.full_name) == func.lower(player_name)
    )
    user = session.exec(stmt_user).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Player not found")
    
    position = getattr(user, "position", "Joueur")  # TODO: Add position field to User model
    team_id = user.team_id
    
    # Get all player sessions (for max calculation) with split_name='all'
    stmt_all = select(CatapultSession).where(
        CatapultSession.user_id == user.id,
        CatapultSession.split_name == "all"
    )
    all_player_sessions_db = session.exec(stmt_all).all()
    all_player_sessions = [s.model_dump() for s in all_player_sessions_db]
    
    # Get player sessions for the week
    player_sessions_db = []
    for s in all_player_sessions_db:
        try:
            session_date = datetime.strptime(s.date, '%Y-%m-%d')
            if target_monday <= session_date <= target_sunday:
                player_sessions_db.append(s)
        except (ValueError, AttributeError, TypeError):
            continue
    
    if not player_sessions_db:
        raise HTTPException(status_code=404, detail="No sessions found for this player in this week")
    
    player_sessions = [s.model_dump() for s in player_sessions_db]
    
    # Get all team sessions for the week (split_name='all')
    stmt_team = select(CatapultSession).join(
        User, CatapultSession.user_id == User.id
    ).where(
        User.team_id == team_id,
        CatapultSession.split_name == "all"
    )
    all_team_sessions = session.exec(stmt_team).all()
    
    # Filter by date
    team_sessions_db = []
    for s in all_team_sessions:
        try:
            session_date = datetime.strptime(s.date, '%Y-%m-%d')
            if target_monday <= session_date <= target_sunday:
                team_sessions_db.append(s)
        except (ValueError, AttributeError, TypeError):
            continue
    
    team_sessions = [s.model_dump() for s in team_sessions_db]
    
    # Get same position sessions for the week (same position as player)
    if position and position != "Joueur":
        # Filter team sessions to only include players with the same position
        stmt_same_position = select(CatapultSession).join(
            User, CatapultSession.user_id == User.id
        ).where(
            User.team_id == team_id,
            User.position == position,
            CatapultSession.split_name == "all"
        )
        same_position_all = session.exec(stmt_same_position).all()
        
        # Filter by date
        same_position_db = []
        for s in same_position_all:
            try:
                session_date = datetime.strptime(s.date, '%Y-%m-%d')
                if target_monday <= session_date <= target_sunday:
                    same_position_db.append(s)
            except (ValueError, AttributeError, TypeError):
                continue
        
        same_position_sessions = [s.model_dump() for s in same_position_db]
    else:
        # Fallback to team sessions if position not defined
        same_position_sessions = team_sessions
    
    # Generate report
    img_base64 = IndividualWeekReportGenerator.generate_individual_week_report(
        player_sessions=player_sessions,
        all_player_sessions=all_player_sessions,
        same_position_sessions=same_position_sessions,
        team_sessions=team_sessions,
        player_name=player_name,
        position=position,
        week_number=week,
        year=year,
        week_start=week_start,
        week_end=week_end
    )
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


@router.get("/players/{player_name}/stats")
def get_player_stats(
    player_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """Get player statistics over the last 3 months"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Calculate date 3 months ago
    three_months_ago = datetime.now() - timedelta(days=90)
    
    # Get all sessions for this player in the last 3 months
    statement = select(CatapultSession).where(
        CatapultSession.player_name == player_name,
        CatapultSession.created_at >= three_months_ago
    )
    sessions = session.exec(statement).all()
    
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this player")
    
    # Calculate statistics
    sessions_count = len(sessions)
    
    # Calculate HSR (speed zones 3+4+5) for each session
    hsr_values = [(s.speed_zone_3_km + s.speed_zone_4_km + s.speed_zone_5_km) * 1000 for s in sessions]
    
    stats = {
        "player_name": player_name,
        "sessions_count": sessions_count,
        "vitesse_max": max([s.top_speed for s in sessions]),
        "vitesse_avg": sum([s.top_speed for s in sessions]) / sessions_count,
        "hsr_max": max(hsr_values),
        "hsr_avg": sum(hsr_values) / sessions_count,
        "sprint_max": max([s.sprint_distance_m for s in sessions]),
        "sprint_avg": sum([s.sprint_distance_m for s in sessions]) / sessions_count,
        "distance_max": max([s.distance_km for s in sessions]) * 1000,
        "distance_avg": sum([s.distance_km for s in sessions]) * 1000 / sessions_count,
        "dec_max": max([s.impacts for s in sessions]),
        "dec_avg": sum([s.impacts for s in sessions]) / sessions_count,
        "pp_max": max([s.power_plays for s in sessions]),
        "pp_avg": sum([s.power_plays for s in sessions]) / sessions_count,
    }
    
    return stats

@router.get("/players/{player_name}/session/{session_id}/report")
def get_player_session_report(
    player_name: str,
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Retourne les stats détaillées d'un joueur pour une session donnée (pour affichage individuel ou comparaison)
    """
    db_session = session.get(CatapultSession, session_id)
    if not db_session or db_session.player_name != player_name:
        raise HTTPException(status_code=404, detail="Session not found for this player")
    return db_session.model_dump()


@router.post("/players/{player_name}/selected-session")
def set_selected_session(
    player_name: str,
    data: dict = Body(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Enregistre la session sélectionnée pour un joueur
    """
    session_id = data.get("session_id")
    user = session.exec(select(User).where(User.player_name == player_name)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.selected_catapult_session_id = session_id
    session.add(user)
    session.commit()
    return {"ok": True}

@router.get("/players/{player_name}/selected-session")
def get_selected_session(
    player_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Retourne la session sélectionnée pour un joueur
    """
    user = session.exec(select(User).where(User.player_name == player_name)).first()
    if not user or not getattr(user, "selected_catapult_session_id", None):
        raise HTTPException(status_code=404, detail="No selected session")
    return {"session_id": user.selected_catapult_session_id}

@router.get("/reports/session/json")
def get_player_session_stats_json(
    session_title: str,
    player_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    # Récupérer toutes les lignes de la session
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    session_data = [s.model_dump() for s in db_sessions]

    # Récupérer toutes les sessions pour les benchmarks
    all_sessions_db = session.exec(select(CatapultSession)).all()
    all_sessions = [s.model_dump() for s in all_sessions_db]

    stats = SessionReportGenerator.get_player_session_stats_json(session_data, all_sessions, player_name)
    return stats


@router.get("/players")
async def get_all_players(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    """
    Retourne la liste unique de tous les joueurs ayant des données Catapult
    """
    # Récupérer tous les noms de joueurs uniques
    query = select(distinct(CatapultSession.player_name)).where(
        CatapultSession.player_name.is_not(None),
        CatapultSession.player_name != ""
    ).order_by(CatapultSession.player_name)
    
    result = session.exec(query).all()
    
    return [name for name in result if name]




@router.get("/players-by-week")
def get_players_by_week(
    week: int,
    year: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
) -> list:
    """Get list of unique player names who had at least one session in the given ISO week"""
    from datetime import datetime, timedelta
    
    # Calculate week start and end dates
    jan_4 = datetime(year, 1, 4)
    week_start = jan_4 - timedelta(days=jan_4.weekday()) + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Query for distinct player names with sessions in the week
    stmt = select(distinct(CatapultSession.player_name)).where(
        CatapultSession.date >= week_start.strftime('%Y-%m-%d'),
        CatapultSession.date <= week_end.strftime('%Y-%m-%d'),
        CatapultSession.split_name == "all",
        CatapultSession.player_name.is_not(None),
        CatapultSession.player_name != ""
    ).order_by(CatapultSession.player_name)
    
    results = session.exec(stmt).all()
    return sorted([name for name in results if name])


@router.get("/sessions/players")
def get_session_players_q(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
) -> list:
    """Get list of unique player names for a specific session (query param)
    """
    stmt = select(User.player_name).join(
        CatapultSession, CatapultSession.user_id == User.id
    ).where(
        CatapultSession.session_title == session_title,
        CatapultSession.split_name == "all"
    ).distinct()

    results = session.exec(stmt).all()
    return sorted([r for r in results if r])



@router.get("/sessions/players-by-title")
def get_session_players_by_title(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
) -> list:
    """Get list of unique player names for a specific session (query param, no slashes issues)
    """
    stmt = select(User.player_name).join(
        CatapultSession, CatapultSession.user_id == User.id
    ).where(
        CatapultSession.session_title == session_title,
        CatapultSession.split_name == "all"
    ).distinct()

    results = session.exec(stmt).all()
    return sorted([r for r in results if r])



@router.get("/session-players-by-title")
def get_session_players_global(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
) -> list:
    """Get list of unique player names for a specific session (no path conflicts)
    """
    stmt = select(User.player_name).join(
        CatapultSession, CatapultSession.user_id == User.id
    ).where(
        CatapultSession.session_title == session_title,
        CatapultSession.split_name == "all"
    ).distinct()

    results = session.exec(stmt).all()
    return sorted([r for r in results if r])


@router.post("/players/{player_name}/radar-chart")
async def generate_radar_chart(
    player_name: str,
    stats: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Make a radar chart for the player's stats (expects keys: minutes, distance, hsr, sprint, vmax, dec, pp, m_min)"""
    try:
        # Crée le graphique
        fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(projection='polar'))
        
        labels = ['Minutes', 'Distance', 'HSR', 'Sprint', 'Vmax', 'DEC', 'PP', 'M/MIN']
        values = [
            stats.get('minutes', 0),
            stats.get('distance', 0),
            stats.get('hsr', 0),
            stats.get('sprint', 0),
            stats.get('vmax', 0),
            stats.get('dec', 0),
            stats.get('pp', 0),
            stats.get('m_min', 0)
        ]
        
        # Normalise chaque métrique indépendamment avec nouvelles limites maximales
        max_vals = [200, 10000, 3000, 1500, 30, 50, 50, 100]
        raw_values = values.copy()  # Garde les valeurs réelles
        normalized_values = [(v / m * 100) if v and m else 0 for v, m in zip(values, max_vals)]
        normalized_values = [min(v, 100) for v in normalized_values]
        
        # Ajoute le premier point à la fin pour fermer le polygone
        plot_values = normalized_values + normalized_values[:1]
        angles = [n / len(labels) * 2 * 3.14159 for n in range(len(labels))]
        angles += angles[:1]
        
        ax.plot(angles, plot_values, 'o-', linewidth=2, color='#3b82f6')
        ax.fill(angles, plot_values, alpha=0.25, color='#3b82f6')
        ax.set_xticks(angles[:-1])
        ax.set_ylim(0, 120)
        
        # Enlever les nombres sur les anneaux (20, 40, 60, 80, 100)
        ax.set_yticks([])
        
        # Ajoute les valeurs réelles du joueur SOUS les noms des axes
        for i, (angle, label, raw_val) in enumerate(zip(angles[:-1], labels, raw_values)):
            # Position du texte plus loin que le graphique
            text_radius = 115
            display_val = f'{raw_val:.1f}' if raw_val < 100 else f'{raw_val:.0f}'
            # Afficher le nom de la métrique ET la valeur en dessous
            ax.text(angle, text_radius, f'{label}\n{display_val}', ha='center', va='bottom', 
                   fontsize=8, fontweight='bold', color='#1f2937')
        
        # Redéfinir les xticks labels comme vides (pour qu'elles n'apparaissent pas au-dessus)
        ax.set_xticklabels([])
        
        ax.grid(True)
        
        # Convertis en base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return {"image": f"data:image/png;base64,{image_base64}"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------
# "Me" convenience endpoints (read-only for the authenticated user)
# ---------------------
@router.get('/me/stats')
def get_my_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'player_name', None):
        raise HTTPException(status_code=404, detail='No player_name set for current user')
    return get_player_stats(current_user.player_name, session, current_user)


@router.get('/me/sessions')
def get_my_sessions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'player_name', None):
        raise HTTPException(status_code=404, detail='No player_name set for current user')
    return get_player_sessions(current_user.player_name, session, current_user)


@router.get('/me/selected-session')
def get_my_selected_session(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'player_name', None):
        raise HTTPException(status_code=404, detail='No player_name set for current user')
    return get_selected_session(current_user.player_name, session, current_user)


@router.get('/me/session/{session_id}/report')
def get_my_session_report(
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'player_name', None):
        raise HTTPException(status_code=404, detail='No player_name set for current user')
    return get_player_session_report(current_user.player_name, session_id, session, current_user)


@router.get('/me/reports/session/json')
def get_my_session_stats_json(
    session_title: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not getattr(current_user, 'player_name', None):
        raise HTTPException(status_code=404, detail='No player_name set for current user')
    return get_player_session_stats_json(session_title, current_user.player_name, session, current_user)


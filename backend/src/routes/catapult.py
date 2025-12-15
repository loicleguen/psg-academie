from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response
from sqlmodel import Session, select
from typing import List, Dict, Any
import pandas as pd
import base64

from ..db.database import get_session
from ..models.catapult import CatapultSession, CatapultSessionCreate
from ..services.catapult_parser import CatapultCSVParser
from ..services.split_detector import SplitDetector
from ..services.graph_generator import CatapultGraphGenerator
from ..services.report_generator import SessionReportGenerator

router = APIRouter(prefix="/catapult", tags=["Catapult GPS Data"])


@router.post("/upload", response_model=Dict[str, Any])
async def upload_catapult_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    Upload and process a Catapult CSV file
    
    - Parses the CSV
    - Stores data in database
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
    
    # Store in database
    stored_sessions = []
    for data in parsed_data:
        session_create = CatapultSessionCreate(**data)
        db_session = CatapultSession(**session_create.model_dump())
        session.add(db_session)
        stored_sessions.append(db_session)
    
    session.commit()
    
    # Generate summary
    summary = CatapultCSVParser.get_session_summary(parsed_data)
    summary["records_stored"] = len(stored_sessions)
    summary["filename"] = file.filename
    
    return summary


@router.get("/sessions", response_model=List[CatapultSession])
def get_all_sessions(session: Session = Depends(get_session)):
    """Get all Catapult training sessions"""
    sessions = session.exec(select(CatapultSession)).all()
    return sessions


@router.get("/sessions/title/{session_title}")
def get_sessions_by_title(session_title: str, session: Session = Depends(get_session)):
    """Get all sessions with a specific title"""
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    sessions = session.exec(statement).all()
    return sessions


@router.get("/sessions/player/{player_name}")
def get_player_sessions(player_name: str, session: Session = Depends(get_session)):
    """Get all sessions for a specific player"""
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    sessions = session.exec(statement).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=CatapultSession)
def get_session_by_id(session_id: int, session: Session = Depends(get_session)):
    """Get a specific Catapult training session by ID"""
    db_session = session.get(CatapultSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


@router.post("/analyze/session/{session_title}")
def analyze_session(session_title: str, session: Session = Depends(get_session)):
    """
    Analyze a training session with split detection and player comparison
    
    Returns:
    - Session summary
    - Split categorization
    - Player comparison
    """
    # Get all data for this session
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict for analysis
    session_data = [s.model_dump() for s in db_sessions]
    
    # Detect and categorize splits
    categorized_splits = SplitDetector.detect_splits_from_aggregated(session_data)
    
    # Compare players
    player_comparison = SplitDetector.compare_splits_across_players(session_data)
    
    # Get session summary
    summary = CatapultCSVParser.get_session_summary(session_data)
    
    return {
        "summary": summary,
        "split_categories": {
            split_type: len(sessions) 
            for split_type, sessions in categorized_splits.items()
        },
        "player_comparison": player_comparison.to_dict('records'),
        "total_players": len(player_comparison)
    }


@router.post("/analyze/player/{player_name}")
def analyze_player(
    player_name: str,
    session_title: str = None,
    session: Session = Depends(get_session)
):
    """
    Analyze a player's performance across all splits
    
    Optional: filter by session_title
    """
    # Build query
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    if session_title:
        statement = statement.where(CatapultSession.session_title == session_title)
    
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found for player")
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    
    # Analyze splits
    analysis = SplitDetector.analyze_player_splits(session_data)
    
    return analysis


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, session: Session = Depends(get_session)):
    """Delete a Catapult session"""
    db_session = session.get(CatapultSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.delete(db_session)
    session.commit()
    
    return {"message": "Session deleted successfully"}


@router.delete("/sessions/title/{session_title}")
def delete_sessions_by_title(session_title: str, session: Session = Depends(get_session)):
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


@router.post("/graphs/player/{player_name}")
def generate_player_graphs(
    player_name: str,
    session_title: str = None,
    session: Session = Depends(get_session)
):
    """
    Generate all graphs for a specific player
    
    Returns base64-encoded images for:
    - Speed zones distribution
    - Intensity timeline
    - Distance breakdown
    - Performance radar
    """
    # Get player sessions
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    if session_title:
        statement = statement.where(CatapultSession.session_title == session_title)
    
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found for player")
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    
    graphs = {}
    
    # If only one session, generate single-session graphs
    if len(session_data) == 1:
        data = session_data[0]
        graphs["speed_zones"] = CatapultGraphGenerator.generate_speed_zones_distribution(data)
        graphs["distance_breakdown"] = CatapultGraphGenerator.generate_distance_breakdown(data)
    
    # If multiple splits, generate timeline
    if len(session_data) > 1:
        graphs["intensity_timeline"] = CatapultGraphGenerator.generate_intensity_timeline(session_data)
    
    return {
        "player_name": player_name,
        "session_title": session_title or "All sessions",
        "graphs": graphs
    }


@router.post("/graphs/session/{session_title}")
def generate_session_graphs(
    session_title: str,
    session: Session = Depends(get_session)
):
    """
    Generate comparison graphs for all players in a session
    
    Returns base64-encoded images comparing all players
    """
    # Get all data for this session
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    
    # Generate comparison graphs
    graphs = CatapultGraphGenerator.generate_player_comparison(
        session_data,
        metrics=["distance_km", "top_speed", "player_load", "energy_kcal", "sprint_distance_m"]
    )
    
    return {
        "session_title": session_title,
        "total_players": len(set(s["player_name"] for s in session_data)),
        "graphs": graphs
    }


@router.get("/graphs/session/{session_title}/{metric}.png")
def get_session_graph_image(
    session_title: str,
    metric: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific comparison graph as PNG image
    
    Available metrics: distance_km, top_speed, player_load, energy_kcal, sprint_distance_m
    """
    # Get all data for this session
    statement = select(CatapultSession).where(CatapultSession.session_title == session_title)
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    
    # Generate comparison graphs
    graphs = CatapultGraphGenerator.generate_player_comparison(
        session_data,
        metrics=[metric]
    )
    
    if metric not in graphs:
        raise HTTPException(status_code=404, detail=f"Metric '{metric}' not found or not available")
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(graphs[metric])
    
    return Response(content=img_binary, media_type="image/png")


@router.get("/graphs/player/{player_name}/speed_zones.png")
def get_player_speed_zones_image(
    player_name: str,
    session_title: str = None,
    session: Session = Depends(get_session)
):
    """
    Get player's speed zones distribution as PNG image
    """
    # Get player sessions
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    if session_title:
        statement = statement.where(CatapultSession.session_title == session_title)
    
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found for player")
    
    # Use first session for single-session graphs
    session_data = db_sessions[0].model_dump()
    
    # Generate graph
    img_base64 = CatapultGraphGenerator.generate_speed_zones_distribution(session_data)
    
    if not img_base64:
        raise HTTPException(status_code=404, detail="No speed zone data available")
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


@router.get("/graphs/player/{player_name}/distance_breakdown.png")
def get_player_distance_breakdown_image(
    player_name: str,
    session_title: str = None,
    session: Session = Depends(get_session)
):
    """
    Get player's distance breakdown as PNG image
    """
    # Get player sessions
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    if session_title:
        statement = statement.where(CatapultSession.session_title == session_title)
    
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found for player")
    
    # Use first session
    session_data = db_sessions[0].model_dump()
    
    # Generate graph
    img_base64 = CatapultGraphGenerator.generate_distance_breakdown(session_data)
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


@router.get("/graphs/player/{player_name}/intensity_timeline.png")
def get_player_intensity_timeline_image(
    player_name: str,
    session_title: str = None,
    session: Session = Depends(get_session)
):
    """
    Get player's intensity timeline as PNG image (requires multiple splits)
    """
    # Get player sessions
    statement = select(CatapultSession).where(CatapultSession.player_name == player_name)
    if session_title:
        statement = statement.where(CatapultSession.session_title == session_title)
    
    db_sessions = session.exec(statement).all()
    
    if not db_sessions:
        raise HTTPException(status_code=404, detail="No sessions found for player")
    
    if len(db_sessions) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 splits for timeline")
    
    # Convert to dict
    session_data = [s.model_dump() for s in db_sessions]
    
    # Generate graph
    img_base64 = CatapultGraphGenerator.generate_intensity_timeline(session_data)
    
    # Decode base64 to binary image
    img_binary = base64.b64decode(img_base64)
    
    return Response(content=img_binary, media_type="image/png")


# ============================================================================
# SESSION REPORTS - Professional training reports
# ============================================================================

@router.post("/reports/session")
def generate_session_report(
    session_title: str,
    session: Session = Depends(get_session)
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


@router.get("/reports/session/{session_title}.png")
def get_session_report_image(
    session_title: str,
    session: Session = Depends(get_session)
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

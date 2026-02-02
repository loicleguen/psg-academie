# Remplacer la fonction get_sessions dans src/routes/catapult.py lignes 125-131

@router.get("/sessions")
def get_sessions(db: Session = Depends(get_session)):
    """Get list of all sessions with summary info"""
    from sqlalchemy import func, desc
    
    # Get session summaries with title, latest date, and player count
    stmt = select(
        CatapultSession.session_title,
        func.max(CatapultSession.session_date).label('session_date'),
        func.count(func.distinct(CatapultSession.user_id)).label('player_count')
    ).group_by(
        CatapultSession.session_title
    ).order_by(
        desc(func.max(CatapultSession.session_date))
    )
    
    results = db.execute(stmt).all()
    
    return [
        {
            "session_title": row[0],
            "session_date": row[1],
            "player_count": row[2]
        }
        for row in results
    ]

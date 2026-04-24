from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from ..db.database import get_session
from ..middleware.security import get_current_user
from ..models.calendar import (
    CalendarEvent,
    CalendarEventCreate,
    CalendarEventRead,
    CalendarEventStatus,
    CalendarEventType,
    CalendarEventUpdate,
    CalendarEventVisibility,
)
from ..models.user import User

router = APIRouter(prefix="/calendar", tags=["Calendar"])

CALENDAR_EDITOR_ROLES = {"admin", "coach", "analyst"}

TYPE_LABELS = {
    "training": "Entrainement",
    "match": "Match",
    "meeting": "Reunion",
    "medical": "Medical",
    "travel": "Deplacement",
    "rest": "Repos",
    "other": "Autre",
}

TYPE_COLORS = {
    "training": "#2563eb",
    "match": "#16a34a",
    "meeting": "#7c3aed",
    "medical": "#dc2626",
    "travel": "#ea580c",
    "rest": "#64748b",
    "other": "#0891b2",
}

STAFF_TARGET = "staff"
WEEKDAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def _role_value(user: User) -> str:
    role = getattr(user, "role", "")
    if hasattr(role, "value"):
        return str(role.value).lower()
    return str(role).split(".")[-1].lower()


def _is_calendar_editor(user: User) -> bool:
    return _role_value(user) in CALENDAR_EDITOR_ROLES


def _event_type_value(event_type: CalendarEventType | str | None) -> str:
    if event_type is None:
        return "other"
    if hasattr(event_type, "value"):
        return str(event_type.value)
    return str(event_type)


def _event_type_label(event: CalendarEvent) -> str:
    custom = (getattr(event, "custom_type_label", None) or "").strip()
    if custom:
        return custom
    return TYPE_LABELS.get(_event_type_value(event.event_type), "Autre")


def _event_color(event: CalendarEvent) -> str:
    if event.color:
        return event.color
    return TYPE_COLORS.get(_event_type_value(event.event_type), TYPE_COLORS["other"])


def _clean_custom_type_label(value: Optional[str]) -> Optional[str]:
    cleaned = " ".join((value or "").split()).strip()
    return cleaned or None


def require_calendar_editor(current_user: User = Depends(get_current_user)) -> User:
    if not _is_calendar_editor(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to edit calendar events",
        )
    return current_user


def _validate_event_payload(
    start_at: datetime,
    end_at: datetime,
    visibility: CalendarEventVisibility,
    team_id: Optional[int],
) -> None:
    if end_at <= start_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_at must be after start_at",
        )
    if visibility == CalendarEventVisibility.TEAM and team_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="team_id is required for team visibility",
        )


def _normalized_event_payload(event_data: CalendarEventCreate | CalendarEventUpdate):
    payload = event_data.model_dump(exclude_unset=True)
    if "custom_type_label" in payload:
        payload["custom_type_label"] = _clean_custom_type_label(
            payload.get("custom_type_label")
        )
    return payload


def _base_visible_events_query(current_user: User):
    stmt = select(CalendarEvent)

    if _is_calendar_editor(current_user):
        return stmt

    visibility_filters = [
        CalendarEvent.visibility == CalendarEventVisibility.ALL,
        CalendarEvent.visibility == CalendarEventVisibility.PLAYERS,
        CalendarEvent.created_by_id == current_user.id,
    ]

    if current_user.team_id:
        visibility_filters.append(
            and_(
                CalendarEvent.visibility == CalendarEventVisibility.TEAM,
                CalendarEvent.team_id == current_user.team_id,
            )
        )

    return stmt.where(or_(*visibility_filters))


def _apply_event_filters(
    stmt,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    team_id: Optional[int],
    target: Optional[str],
    event_type: Optional[CalendarEventType],
    include_cancelled: bool,
):
    if from_date:
        stmt = stmt.where(CalendarEvent.end_at >= from_date)
    if to_date:
        stmt = stmt.where(CalendarEvent.start_at <= to_date)
    if team_id:
        stmt = stmt.where(CalendarEvent.team_id == team_id)
    if target == STAFF_TARGET:
        stmt = stmt.where(CalendarEvent.visibility == CalendarEventVisibility.STAFF)
    if event_type:
        stmt = stmt.where(CalendarEvent.event_type == event_type)
    if not include_cancelled:
        stmt = stmt.where(CalendarEvent.status != CalendarEventStatus.CANCELLED)
    return stmt.order_by(CalendarEvent.start_at)


def _load_visible_events(
    session: Session,
    current_user: User,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    team_id: Optional[int],
    target: Optional[str],
    event_type: Optional[CalendarEventType],
    include_cancelled: bool,
) -> list[CalendarEvent]:
    stmt = _base_visible_events_query(current_user)
    stmt = _apply_event_filters(
        stmt,
        from_date=from_date,
        to_date=to_date,
        team_id=team_id,
        target=target,
        event_type=event_type,
        include_cancelled=include_cancelled,
    )
    return session.exec(stmt).all()


def _get_visible_event_or_404(
    event_id: int,
    session: Session,
    current_user: User,
) -> CalendarEvent:
    stmt = _base_visible_events_query(current_user).where(CalendarEvent.id == event_id)
    event = session.exec(stmt).first()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return event


def _ics_escape(value: Optional[str]) -> str:
    if not value:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _format_ics_datetime(value: datetime, all_day: bool, timezone: str) -> str:
    if all_day:
        return f";VALUE=DATE:{value.strftime('%Y%m%d')}"
    return f";TZID={timezone}:{value.strftime('%Y%m%dT%H%M%S')}"


def _build_ics(events: list[CalendarEvent]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PSG Academie//Training Calendar//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
        timezone = event.timezone or "Europe/Paris"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:psg-academie-calendar-{event.id}@psg-academie.local",
                f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART{_format_ics_datetime(event.start_at, event.all_day, timezone)}",
                f"DTEND{_format_ics_datetime(event.end_at, event.all_day, timezone)}",
                f"SUMMARY:{_ics_escape(event.title)}",
                f"DESCRIPTION:{_ics_escape(event.description)}",
                f"LOCATION:{_ics_escape(event.location)}",
                f"CATEGORIES:{_ics_escape(_event_type_label(event))}",
                f"STATUS:{'CANCELLED' if event.status == CalendarEventStatus.CANCELLED else 'CONFIRMED'}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/events", response_model=List[CalendarEventRead])
def list_calendar_events(
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    team_id: Optional[int] = None,
    target: Optional[str] = None,
    event_type: Optional[CalendarEventType] = None,
    include_cancelled: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return _load_visible_events(
        session=session,
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
        team_id=team_id,
        target=target,
        event_type=event_type,
        include_cancelled=include_cancelled,
    )


@router.post(
    "/events",
    response_model=CalendarEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_calendar_event(
    event_data: CalendarEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_calendar_editor),
):
    _validate_event_payload(
        event_data.start_at,
        event_data.end_at,
        event_data.visibility,
        event_data.team_id,
    )

    event = CalendarEvent(**_normalized_event_payload(event_data), created_by_id=current_user.id)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/events/{event_id}", response_model=CalendarEventRead)
def get_calendar_event(
    event_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return _get_visible_event_or_404(event_id, session, current_user)


@router.patch("/events/{event_id}", response_model=CalendarEventRead)
def update_calendar_event(
    event_id: int,
    event_update: CalendarEventUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_calendar_editor),
):
    event = session.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    update_data: dict[str, Any] = _normalized_event_payload(event_update)
    for field, value in update_data.items():
        setattr(event, field, value)

    _validate_event_payload(
        event.start_at,
        event.end_at,
        event.visibility,
        event.team_id,
    )
    event.updated_at = datetime.utcnow()

    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_200_OK)
def delete_calendar_event(
    event_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_calendar_editor),
):
    event = session.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    session.delete(event)
    session.commit()
    return {"message": "Calendar event deleted successfully"}


@router.get("/export.ics")
def export_calendar_ics(
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    team_id: Optional[int] = None,
    target: Optional[str] = None,
    event_type: Optional[CalendarEventType] = None,
    include_cancelled: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    events = _load_visible_events(
        session=session,
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
        team_id=team_id,
        target=target,
        event_type=event_type,
        include_cancelled=include_cancelled,
    )
    return Response(
        content=_build_ics(events),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="psg-calendar.ics"'},
    )


def _format_pdf_date(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")


def _view_kind(view: str) -> str:
    normalized = (view or "").lower()
    if "month" in normalized:
        return "month"
    if "day" in normalized and "month" not in normalized:
        return "day"
    return "week"


def _range_start(from_date: Optional[datetime]) -> date:
    return (from_date or datetime.utcnow()).date()


def _range_end(from_date: Optional[datetime], to_date: Optional[datetime], kind: str) -> date:
    if to_date:
        # FullCalendar sends an exclusive end. Subtract one day for display ranges.
        return (to_date - timedelta(days=1)).date()
    start = _range_start(from_date)
    if kind == "month":
        return start + timedelta(days=41)
    if kind == "day":
        return start
    return start + timedelta(days=6)


def _event_overlaps_day(event: CalendarEvent, day: date) -> bool:
    event_start = event.start_at.date()
    event_end = event.end_at.date()
    return event_start <= day <= event_end


def _events_for_day(events: list[CalendarEvent], day: date) -> list[CalendarEvent]:
    return sorted(
        [event for event in events if _event_overlaps_day(event, day)],
        key=lambda event: (event.start_at.time(), event.end_at.time(), event.title),
    )


def _truncate(value: str, max_chars: int) -> str:
    value = " ".join((value or "").split())
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3]}..."


def _event_pdf_label(event: CalendarEvent, include_time: bool = True) -> str:
    prefix = ""
    if include_time and not event.all_day:
        prefix = f"{event.start_at.strftime('%H:%M')} "
    return f"{prefix}{event.title}"


def _minutes_since_midnight(value: datetime) -> int:
    return value.hour * 60 + value.minute


def _time_bounds_for_events(events: list[CalendarEvent]) -> tuple[int, int]:
    timed_events = [event for event in events if not event.all_day]
    if not timed_events:
        return (8 * 60, 20 * 60)

    min_start = min(_minutes_since_midnight(event.start_at) for event in timed_events)
    max_end = max(_minutes_since_midnight(event.end_at) for event in timed_events)
    start_hour = max(0, min_start // 60 - 1)
    end_hour = min(24, (max_end + 59) // 60 + 1)
    if end_hour <= start_hour:
        end_hour = min(24, start_hour + 2)
    return (start_hour * 60, end_hour * 60)


def _time_to_y(minutes: int, min_minutes: int, max_minutes: int, bottom: float, height: float) -> float:
    clamped = max(min_minutes, min(max_minutes, minutes))
    ratio = (clamped - min_minutes) / max(1, max_minutes - min_minutes)
    return bottom + height * (1 - ratio)


def _date_range_label(start: date, end: date, kind: str) -> str:
    if kind == "day":
        return start.strftime("%d/%m/%Y")
    return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"


def _draw_pdf_header(ax, title: str, subtitle: str, event_count: int) -> None:
    ax.text(
        0.03,
        0.955,
        title,
        fontsize=20,
        fontweight="bold",
        color="#111827",
        transform=ax.transAxes,
    )
    ax.text(
        0.03,
        0.925,
        subtitle,
        fontsize=10,
        color="#475569",
        transform=ax.transAxes,
    )
    ax.text(
        0.97,
        0.925,
        f"{event_count} evenement(s)",
        fontsize=10,
        color="#475569",
        ha="right",
        transform=ax.transAxes,
    )


def _draw_month_pdf(ax, events: list[CalendarEvent], start: date, end: date) -> None:
    from matplotlib.patches import Rectangle

    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)

    rows = max(1, (len(days) + 6) // 7)
    grid_left = 0.03
    grid_bottom = 0.07
    grid_width = 0.94
    grid_height = 0.80
    col_width = grid_width / 7
    row_height = grid_height / rows

    for col, label in enumerate(WEEKDAY_LABELS):
        ax.text(
            grid_left + col * col_width + col_width / 2,
            grid_bottom + grid_height + 0.012,
            label,
            fontsize=9,
            fontweight="bold",
            color="#334155",
            ha="center",
            transform=ax.transAxes,
        )

    for index, day in enumerate(days):
        row = index // 7
        col = index % 7
        x = grid_left + col * col_width
        y = grid_bottom + grid_height - (row + 1) * row_height

        ax.add_patch(
            Rectangle(
                (x, y),
                col_width,
                row_height,
                fill=False,
                edgecolor="#cbd5e1",
                linewidth=0.8,
                transform=ax.transAxes,
            )
        )
        ax.text(
            x + 0.006,
            y + row_height - 0.025,
            str(day.day),
            fontsize=9,
            fontweight="bold",
            color="#111827",
            transform=ax.transAxes,
        )

        day_events = _events_for_day(events, day)
        max_events = max(1, int((row_height - 0.04) / 0.023))
        for event_index, event in enumerate(day_events[:max_events]):
            event_y = y + row_height - 0.052 - event_index * 0.023
            color = _event_color(event)
            ax.add_patch(
                Rectangle(
                    (x + 0.006, event_y - 0.012),
                    col_width - 0.012,
                    0.018,
                    color=color,
                    alpha=0.9,
                    transform=ax.transAxes,
                )
            )
            ax.text(
                x + 0.01,
                event_y - 0.008,
                _truncate(_event_pdf_label(event), 22),
                fontsize=6.4,
                color="white",
                fontweight="bold",
                transform=ax.transAxes,
            )
        if len(day_events) > max_events:
            ax.text(
                x + 0.01,
                y + 0.008,
                f"+{len(day_events) - max_events} autre(s)",
                fontsize=6.5,
                color="#475569",
                transform=ax.transAxes,
            )


def _draw_week_pdf(ax, events: list[CalendarEvent], start: date) -> None:
    from matplotlib.patches import Rectangle

    days = [start + timedelta(days=offset) for offset in range(7)]
    min_minutes, max_minutes = _time_bounds_for_events(events)
    grid_left = 0.08
    grid_bottom = 0.07
    grid_width = 0.89
    grid_height = 0.80
    col_width = grid_width / 7
    label_left = 0.03
    hour_step = 60

    for minutes in range(min_minutes, max_minutes + 1, hour_step):
        y = _time_to_y(minutes, min_minutes, max_minutes, grid_bottom, grid_height)
        ax.plot(
            [grid_left, grid_left + grid_width],
            [y, y],
            color="#e2e8f0",
            linewidth=0.6,
            transform=ax.transAxes,
        )
        ax.text(
            label_left,
            y - 0.006,
            f"{minutes // 60:02d}:00",
            fontsize=7.2,
            color="#475569",
            ha="left",
            transform=ax.transAxes,
        )

    ax.add_patch(
        Rectangle(
            (grid_left, grid_bottom),
            grid_width,
            grid_height,
            fill=False,
            edgecolor="#cbd5e1",
            linewidth=0.9,
            transform=ax.transAxes,
        )
    )

    for col, day in enumerate(days):
        x = grid_left + col * col_width
        ax.add_patch(
            Rectangle(
                (x, grid_bottom),
                col_width,
                grid_height,
                fill=False,
                edgecolor="#cbd5e1",
                linewidth=0.8,
                transform=ax.transAxes,
            )
        )
        ax.text(
            x + col_width / 2,
            grid_bottom + grid_height + 0.014,
            f"{WEEKDAY_LABELS[col]} {day.strftime('%d/%m')}",
            fontsize=8.5,
            fontweight="bold",
            color="#111827",
            ha="center",
            transform=ax.transAxes,
        )

        day_events = _events_for_day(events, day)
        for event in day_events[:20]:
            color = _event_color(event)
            if event.all_day:
                event_y_top = grid_bottom + grid_height - 0.006
                event_height = 0.028
            else:
                start_minutes = _minutes_since_midnight(event.start_at)
                end_minutes = _minutes_since_midnight(event.end_at)
                event_y_top = _time_to_y(start_minutes, min_minutes, max_minutes, grid_bottom, grid_height)
                event_y_bottom = _time_to_y(end_minutes, min_minutes, max_minutes, grid_bottom, grid_height)
                event_height = max(0.024, event_y_top - event_y_bottom)
                event_y_top = min(grid_bottom + grid_height - 0.004, event_y_top)

            ax.add_patch(
                Rectangle(
                    (x + 0.006, event_y_top - event_height),
                    col_width - 0.012,
                    event_height,
                    color=color,
                    alpha=0.92,
                    transform=ax.transAxes,
                )
            )
            ax.text(
                x + 0.01,
                event_y_top - 0.013,
                _truncate(_event_pdf_label(event), 21),
                fontsize=6.3,
                color="white",
                fontweight="bold",
                transform=ax.transAxes,
            )
            if event_height >= 0.04:
                ax.text(
                    x + 0.01,
                    event_y_top - 0.029,
                    _truncate(_event_type_label(event), 18),
                    fontsize=5.7,
                    color="white",
                    transform=ax.transAxes,
                )


def _draw_day_pdf(ax, events: list[CalendarEvent], day: date) -> None:
    from matplotlib.patches import Rectangle

    day_events = _events_for_day(events, day)
    min_minutes, max_minutes = _time_bounds_for_events(day_events)
    grid_left = 0.10
    grid_bottom = 0.07
    grid_width = 0.87
    grid_height = 0.80
    label_left = 0.03

    for minutes in range(min_minutes, max_minutes + 1, 60):
        y = _time_to_y(minutes, min_minutes, max_minutes, grid_bottom, grid_height)
        ax.plot(
            [grid_left, grid_left + grid_width],
            [y, y],
            color="#e2e8f0",
            linewidth=0.6,
            transform=ax.transAxes,
        )
        ax.text(
            label_left,
            y - 0.006,
            f"{minutes // 60:02d}:00",
            fontsize=7.5,
            color="#475569",
            transform=ax.transAxes,
        )

    ax.add_patch(
        Rectangle(
            (grid_left, grid_bottom),
            grid_width,
            grid_height,
            fill=False,
            edgecolor="#cbd5e1",
            linewidth=0.9,
            transform=ax.transAxes,
        )
    )

    if not day_events:
        ax.text(
            grid_left + 0.02,
            0.82,
            "Aucun evenement sur cette journee.",
            fontsize=12,
            color="#111827",
            transform=ax.transAxes,
        )
        return

    for event in day_events[:18]:
        color = _event_color(event)
        if event.all_day:
            event_y_top = grid_bottom + grid_height - 0.01
            event_height = 0.045
        else:
            start_minutes = _minutes_since_midnight(event.start_at)
            end_minutes = _minutes_since_midnight(event.end_at)
            event_y_top = _time_to_y(start_minutes, min_minutes, max_minutes, grid_bottom, grid_height)
            event_y_bottom = _time_to_y(end_minutes, min_minutes, max_minutes, grid_bottom, grid_height)
            event_height = max(0.04, event_y_top - event_y_bottom)
            event_y_top = min(grid_bottom + grid_height - 0.004, event_y_top)

        ax.add_patch(
            Rectangle(
                (grid_left + 0.012, event_y_top - event_height),
                grid_width - 0.024,
                event_height,
                color=color,
                alpha=0.92,
                transform=ax.transAxes,
            )
        )
        ax.text(
            grid_left + 0.024,
            event_y_top - 0.017,
            _truncate(_event_pdf_label(event), 95),
            fontsize=9,
            fontweight="bold",
            color="white",
            transform=ax.transAxes,
        )
        meta = _event_type_label(event)
        if event.location:
            meta = f"{meta} | {event.location}"
        ax.text(
            grid_left + 0.024,
            event_y_top - 0.035,
            _truncate(meta, 110),
            fontsize=7,
            color="white",
            transform=ax.transAxes,
        )
        if event.description and event_height >= 0.07:
            ax.text(
                grid_left + 0.024,
                event_y_top - 0.055,
                _truncate(event.description.replace("\n", " "), 120),
                fontsize=6.5,
                color="white",
                transform=ax.transAxes,
            )


def _build_pdf(
    events: list[CalendarEvent],
    view: str = "week",
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    buffer = BytesIO()
    kind = _view_kind(view)
    start = _range_start(from_date)
    end = _range_end(from_date, to_date, kind)

    with PdfPages(buffer) as pdf:
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        title = {
            "month": "Calendrier mensuel PSG Academie",
            "week": "Calendrier hebdomadaire PSG Academie",
            "day": "Calendrier journalier PSG Academie",
        }[kind]
        _draw_pdf_header(
            ax,
            title=title,
            subtitle=_date_range_label(start, end, kind),
            event_count=len(events),
        )

        if kind == "month":
            _draw_month_pdf(ax, events, start, end)
        elif kind == "day":
            _draw_day_pdf(ax, events, start)
        else:
            _draw_week_pdf(ax, events, start)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    buffer.seek(0)
    return buffer.getvalue()


@router.get("/export.pdf")
def export_calendar_pdf(
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    team_id: Optional[int] = None,
    target: Optional[str] = None,
    view: str = "week",
    event_type: Optional[CalendarEventType] = None,
    include_cancelled: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    events = _load_visible_events(
        session=session,
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
        team_id=team_id,
        target=target,
        event_type=event_type,
        include_cancelled=include_cancelled,
    )
    return Response(
        content=_build_pdf(events, view=view, from_date=from_date, to_date=to_date),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="psg-calendar.pdf"'},
    )

import { useCallback, useEffect, useMemo, useState } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import frLocale from '@fullcalendar/core/locales/fr';
import { calendarService } from '../services/calendarService';
import { catapultService } from '../services/catapultService';
import { useAuth } from '../context/AuthContext';

const EVENT_TYPES = [
  ['training', 'Entrainement'],
  ['match', 'Match'],
  ['meeting', 'Reunion'],
  ['medical', 'Medical'],
  ['travel', 'Deplacement'],
  ['rest', 'Repos'],
  ['other', 'Autre / personnalise'],
];

const VISIBILITIES = [
  ['all', 'Tout le monde'],
  ['team', 'Equipe'],
  ['staff', 'Staff'],
  ['players', 'Joueurs'],
  ['private', 'Prive'],
];

const STATUSES = [
  ['scheduled', 'Planifie'],
  ['completed', 'Termine'],
  ['cancelled', 'Annule'],
];

const TYPE_COLORS = {
  training: '#2563eb',
  match: '#16a34a',
  meeting: '#7c3aed',
  medical: '#dc2626',
  travel: '#ea580c',
  rest: '#64748b',
  other: '#0891b2',
};

const CUSTOM_COLORS = [
  '#0891b2',
  '#be123c',
  '#9333ea',
  '#0f766e',
  '#ca8a04',
  '#db2777',
  '#4f46e5',
  '#15803d',
];

const STAFF_TARGET = '__staff';

const EMPTY_FORM = {
  title: '',
  event_type: 'training',
  status: 'scheduled',
  visibility: 'all',
  start_at: '',
  end_at: '',
  all_day: false,
  timezone: 'Europe/Paris',
  team_id: '',
  location: '',
  description: '',
  custom_type_label: '',
  color: '',
};

const FORM_INPUT_CLASS =
  'mt-1 w-full h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500';

const TEXTAREA_CLASS =
  'mt-1 w-full min-h-24 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500';

function pad(value) {
  return String(value).padStart(2, '0');
}

function dateToLocalInput(value) {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 16);
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function dateToBackendDateTime(value) {
  if (!value) return '';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).length === 16 ? `${value}:00` : String(value);
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60 * 1000);
}

function optionLabel(options, value) {
  return options.find(([key]) => key === value)?.[1] || value;
}

function hashString(value) {
  return String(value || '')
    .split('')
    .reduce((hash, char) => ((hash << 5) - hash + char.charCodeAt(0)) | 0, 0);
}

function getTypeLabel(source) {
  const customLabel = String(source?.custom_type_label || '').trim();
  if (customLabel) {
    return customLabel;
  }
  return optionLabel(EVENT_TYPES, source?.event_type || 'other');
}

function getAutoEventColor(source) {
  const customLabel = String(source?.custom_type_label || '').trim();
  if (source?.color) {
    return source.color;
  }
  if (customLabel) {
    return CUSTOM_COLORS[Math.abs(hashString(customLabel)) % CUSTOM_COLORS.length];
  }
  return TYPE_COLORS[source?.event_type] || TYPE_COLORS.other;
}

function sortEventsByStart(left, right) {
  return new Date(left.start_at).getTime() - new Date(right.start_at).getTime();
}

function buildPayload(form) {
  const isStaffEvent = form.team_id === STAFF_TARGET;
  return {
    title: form.title.trim(),
    event_type: form.event_type,
    status: form.status,
    visibility: isStaffEvent ? 'staff' : form.visibility,
    start_at: form.start_at,
    end_at: form.end_at,
    all_day: form.all_day,
    timezone: form.timezone || 'Europe/Paris',
    team_id: form.team_id && !isStaffEvent ? Number(form.team_id) : null,
    location: form.location.trim() || null,
    description: form.description.trim() || null,
    custom_type_label:
      form.event_type === 'other' ? form.custom_type_label.trim() || null : null,
    color: null,
  };
}

function eventToForm(event) {
  const isStaffEvent = event.visibility === 'staff' && !event.team_id;
  return {
    title: event.title || '',
    event_type: event.event_type || 'training',
    status: event.status || 'scheduled',
    visibility: event.visibility || 'all',
    start_at: dateToLocalInput(event.start_at),
    end_at: dateToLocalInput(event.end_at),
    all_day: Boolean(event.all_day),
    timezone: event.timezone || 'Europe/Paris',
    team_id: isStaffEvent ? STAFF_TARGET : event.team_id ? String(event.team_id) : '',
    location: event.location || '',
    description: event.description || '',
    custom_type_label: event.custom_type_label || '',
    color: event.color || '',
  };
}

export default function Calendar() {
  const { user } = useAuth();
  const canEdit = ['admin', 'coach', 'analyst'].includes(user?.role);

  const [events, setEvents] = useState([]);
  const [teams, setTeams] = useState([]);
  const [visibleRange, setVisibleRange] = useState(null);
  const [currentView, setCurrentView] = useState('timeGridWeek');
  const [typeFilter, setTypeFilter] = useState('');
  const [teamFilter, setTeamFilter] = useState('');
  const [includeCancelled, setIncludeCancelled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const buildFilters = useCallback(
    (range = visibleRange) => ({
      from: range?.start,
      to: range?.end,
      event_type: typeFilter,
      team_id: teamFilter && teamFilter !== STAFF_TARGET ? teamFilter : '',
      target: teamFilter === STAFF_TARGET ? 'staff' : '',
      include_cancelled: includeCancelled,
    }),
    [includeCancelled, teamFilter, typeFilter, visibleRange]
  );

  const eventMatchesCurrentView = useCallback(
    (event, range = visibleRange) => {
      if (!event || !range) return true;
      const eventStart = new Date(event.start_at).getTime();
      const eventEnd = new Date(event.end_at).getTime();
      const rangeStart = new Date(range.start).getTime();
      const rangeEnd = new Date(range.end).getTime();

      if (Number.isFinite(rangeStart) && Number.isFinite(rangeEnd)) {
        if (eventEnd < rangeStart || eventStart > rangeEnd) {
          return false;
        }
      }
      if (typeFilter && event.event_type !== typeFilter) {
        return false;
      }
      if (teamFilter === STAFF_TARGET && event.visibility !== 'staff') {
        return false;
      }
      if (teamFilter && String(event.team_id || '') !== String(teamFilter)) {
        if (teamFilter === STAFF_TARGET) {
          return true;
        }
        return false;
      }
      if (!includeCancelled && event.status === 'cancelled') {
        return false;
      }
      return true;
    },
    [includeCancelled, teamFilter, typeFilter, visibleRange]
  );

  const upsertEventInState = useCallback(
    (event) => {
      setEvents((currentEvents) => {
        const withoutEvent = currentEvents.filter((item) => item.id !== event.id);
        if (!eventMatchesCurrentView(event)) {
          return withoutEvent;
        }
        return [...withoutEvent, event].sort(sortEventsByStart);
      });
    },
    [eventMatchesCurrentView]
  );

  const loadEvents = useCallback(
    async (range = visibleRange) => {
      if (!range) return;

      try {
        setLoading(true);
        setError('');
        const data = await calendarService.getEvents(buildFilters(range));
        setEvents(data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Erreur lors du chargement du calendrier');
        console.error(err);
      } finally {
        setLoading(false);
      }
    },
    [buildFilters, visibleRange]
  );

  useEffect(() => {
    if (!canEdit) return;

    const loadTeams = async () => {
      try {
        const data = await catapultService.getTeams();
        setTeams(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Erreur chargement equipes:', err);
      }
    };

    loadTeams();
  }, [canEdit]);

  useEffect(() => {
    if (visibleRange) {
      loadEvents(visibleRange);
    }
  }, [includeCancelled, loadEvents, teamFilter, typeFilter, visibleRange]);

  const calendarEvents = useMemo(
    () =>
      events.map((event) => {
        const color =
          event.status === 'cancelled'
            ? '#6b7280'
            : getAutoEventColor(event);

        return {
          id: String(event.id),
          title: event.title,
          start: event.start_at,
          end: event.end_at,
          allDay: event.all_day,
          backgroundColor: color,
          borderColor: color,
          classNames: [`calendar-event-${event.status}`],
          extendedProps: event,
        };
      }),
    [events]
  );

  const openCreateModal = (startDate = new Date(), endDate = addMinutes(new Date(), 90), allDay = false) => {
    setSelectedEventId(null);
    setForm({
      ...EMPTY_FORM,
      start_at: dateToLocalInput(startDate),
      end_at: dateToLocalInput(endDate),
      all_day: allDay,
      color: '',
    });
    setError('');
    setSuccess('');
    setModalOpen(true);
  };

  const openEventModal = (event) => {
    const original = event.extendedProps;
    setSelectedEventId(original.id);
    setForm(eventToForm(original));
    setError('');
    setSuccess('');
    setModalOpen(true);
  };

  const handleDatesSet = (info) => {
    const nextRange = {
      start: info.startStr,
      end: info.endStr,
    };
    setVisibleRange(nextRange);
    setCurrentView(info.view?.type || 'timeGridWeek');
  };

  const handleSelect = (info) => {
    if (!canEdit) return;
    const start = info.start || new Date();
    const end = info.end && info.end > start ? info.end : addMinutes(start, 90);
    openCreateModal(start, end, info.allDay);
  };

  const handleEventDropOrResize = async (info) => {
    if (!canEdit) {
      info.revert();
      return;
    }

    try {
      const updatedEvent = await calendarService.updateEvent(info.event.id, {
        start_at: dateToBackendDateTime(info.event.start),
        end_at: dateToBackendDateTime(info.event.end || addMinutes(info.event.start, 90)),
        all_day: info.event.allDay,
      });
      upsertEventInState(updatedEvent);
    } catch (err) {
      info.revert();
      setError(err.response?.data?.detail || 'Erreur lors du deplacement');
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canEdit) return;

    try {
      setSaving(true);
      setError('');
      const payload = buildPayload(form);
      let savedEvent;

      if (selectedEventId) {
        savedEvent = await calendarService.updateEvent(selectedEventId, payload);
        setSuccess('Evenement modifie');
      } else {
        savedEvent = await calendarService.createEvent(payload);
        setSuccess('Evenement cree');
      }

      upsertEventInState(savedEvent);
      setModalOpen(false);
      loadEvents(visibleRange);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la sauvegarde');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedEventId || !canEdit) return;
    if (!window.confirm('Supprimer cet evenement ?')) return;

    try {
      setSaving(true);
      await calendarService.deleteEvent(selectedEventId);
      setEvents((currentEvents) =>
        currentEvents.filter((event) => String(event.id) !== String(selectedEventId))
      );
      setModalOpen(false);
      loadEvents(visibleRange);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la suppression');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (format) => {
    try {
      setError('');
      const filters = {
        ...buildFilters(),
        view: currentView,
      };
      if (format === 'ics') {
        await calendarService.exportIcs(filters);
      } else {
        await calendarService.exportPdf(filters);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'export");
      console.error(err);
    }
  };

  const selectedTeam = teams.find((team) => String(team.id) === String(form.team_id));
  const selectedTargetLabel = form.team_id === STAFF_TARGET ? 'Staff' : selectedTeam?.name;
  const readonly = !canEdit;

  return (
    <div className="calendar-shell max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="flex flex-col gap-4 mb-6 lg:flex-row lg:items-center lg:justify-between">
          <h1 className="bg-white/60 px-4 py-2 rounded-md text-4xl font-bold text-black">
            Calendrier
          </h1>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => handleExport('ics')}
              className="h-10 rounded-md bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-700"
            >
              Export ICS
            </button>
            <button
              type="button"
              onClick={() => handleExport('pdf')}
              className="h-10 rounded-md bg-slate-900 px-4 text-sm font-bold text-white hover:bg-slate-700"
            >
              Export PDF
            </button>
            {canEdit && (
              <button
                type="button"
                onClick={() => openCreateModal()}
                className="h-10 rounded-md bg-blue-600 px-4 text-sm font-bold text-white hover:bg-blue-700"
              >
                Nouvel evenement
              </button>
            )}
          </div>
        </div>

        <div className="mb-4 grid gap-3 rounded-lg bg-white/80 p-4 shadow md:grid-cols-4">
          <label className="text-sm font-bold text-gray-800">
            Type
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className={FORM_INPUT_CLASS}
            >
              <option value="">Tous</option>
              {EVENT_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm font-bold text-gray-800">
            Equipe
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
              className={FORM_INPUT_CLASS}
              disabled={!canEdit}
            >
              <option value="">Toutes</option>
              <option value={STAFF_TARGET}>Staff</option>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.academy?.country?.name ? `${team.academy.country.name} / ` : ''}
                  {team.academy?.name ? `${team.academy.name} / ` : ''}
                  {team.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-3 pt-7 text-sm font-bold text-gray-800">
            <input
              type="checkbox"
              checked={includeCancelled}
              onChange={(e) => setIncludeCancelled(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Afficher les annules
          </label>

          <div className="flex items-end justify-end text-sm font-bold text-gray-700">
            {loading ? 'Chargement...' : `${events.length} evenement${events.length > 1 ? 's' : ''}`}
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
            {success}
          </div>
        )}

        <div className="rounded-lg bg-white/90 p-4 shadow">
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
            locale={frLocale}
            initialView="timeGridWeek"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
            }}
            buttonText={{
              today: "Aujourd'hui",
              month: 'Mois',
              week: 'Semaine',
              day: 'Jour',
              list: 'Liste',
            }}
            events={calendarEvents}
            selectable={canEdit}
            editable={canEdit}
            eventResizableFromStart={canEdit}
            selectMirror
            nowIndicator
            allDayMaintainDuration
            slotMinTime="07:00:00"
            slotMaxTime="22:00:00"
            firstDay={1}
            datesSet={handleDatesSet}
            select={handleSelect}
            eventClick={(info) => openEventModal(info.event)}
            eventDrop={handleEventDropOrResize}
            eventResize={handleEventDropOrResize}
            eventContent={(info) => (
              <div className="min-w-0 leading-tight">
                <div className="truncate">{info.event.title}</div>
                <div className="truncate text-[10px] font-semibold opacity-85">
                  {getTypeLabel(info.event.extendedProps)}
                </div>
              </div>
            )}
            height="auto"
          />
        </div>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6">
          <form
            onSubmit={handleSubmit}
            className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-2xl"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {selectedEventId ? form.title || 'Evenement' : 'Nouvel evenement'}
                </h2>
                {selectedTargetLabel && (
                  <p className="mt-1 text-sm font-semibold text-gray-500">
                    {selectedTargetLabel}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-md px-3 py-2 text-sm font-bold text-gray-600 hover:bg-gray-100"
              >
                Fermer
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-bold text-gray-800 md:col-span-2">
                Titre
                <input
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                  required
                />
              </label>

              <label className="text-sm font-bold text-gray-800">
                Type
                <select
                  value={form.event_type}
                  onChange={(e) => {
                    const nextType = e.target.value;
                    setForm((prev) => ({
                      ...prev,
                      event_type: nextType,
                      custom_type_label:
                        nextType === 'other' ? prev.custom_type_label : '',
                      color: '',
                    }));
                  }}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                >
                  {EVENT_TYPES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              {form.event_type === 'other' && (
                <label className="text-sm font-bold text-gray-800">
                  Type personnalise
                  <input
                    value={form.custom_type_label}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        custom_type_label: e.target.value,
                        color: '',
                      }))
                    }
                    placeholder="Tournoi, stage, reunion parents..."
                    className={FORM_INPUT_CLASS}
                    disabled={readonly || saving}
                    required
                  />
                </label>
              )}

              <label className="text-sm font-bold text-gray-800">
                Statut
                <select
                  value={form.status}
                  onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                >
                  {STATUSES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm font-bold text-gray-800">
                Debut
                <input
                  type="datetime-local"
                  value={form.start_at}
                  onChange={(e) => setForm((prev) => ({ ...prev, start_at: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                  required
                />
              </label>

              <label className="text-sm font-bold text-gray-800">
                Fin
                <input
                  type="datetime-local"
                  value={form.end_at}
                  onChange={(e) => setForm((prev) => ({ ...prev, end_at: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                  required
                />
              </label>

              <label className="text-sm font-bold text-gray-800">
                Visibilite
                <select
                  value={form.visibility}
                  onChange={(e) => setForm((prev) => ({ ...prev, visibility: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                >
                  {VISIBILITIES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm font-bold text-gray-800">
                Equipe
                <select
                  value={form.team_id}
                  onChange={(e) => {
                    const nextValue = e.target.value;
                    setForm((prev) => ({
                      ...prev,
                      team_id: nextValue,
                      visibility:
                        nextValue === STAFF_TARGET
                          ? 'staff'
                          : prev.visibility === 'staff'
                            ? 'all'
                            : prev.visibility,
                    }));
                  }}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                >
                  <option value="">Aucune</option>
                  <option value={STAFF_TARGET}>Staff</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.academy?.country?.name ? `${team.academy.country.name} / ` : ''}
                      {team.academy?.name ? `${team.academy.name} / ` : ''}
                      {team.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm font-bold text-gray-800">
                Lieu
                <input
                  value={form.location}
                  onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))}
                  className={FORM_INPUT_CLASS}
                  disabled={readonly || saving}
                />
              </label>

              <div className="text-sm font-bold text-gray-800">
                Couleur automatique
                <div className="mt-1 flex h-10 items-center gap-3 rounded-md border border-gray-300 bg-white px-3">
                  <span
                    className="h-5 w-5 rounded-full border border-gray-300"
                    style={{ backgroundColor: getAutoEventColor(form) }}
                  />
                  <span className="text-sm font-semibold text-gray-700">
                    {getTypeLabel(form)}
                  </span>
                </div>
              </div>

              <label className="flex items-center gap-3 text-sm font-bold text-gray-800">
                <input
                  type="checkbox"
                  checked={form.all_day}
                  onChange={(e) => setForm((prev) => ({ ...prev, all_day: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  disabled={readonly || saving}
                />
                Toute la journee
              </label>

              <label className="text-sm font-bold text-gray-800 md:col-span-2">
                Description
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  className={TEXTAREA_CLASS}
                  disabled={readonly || saving}
                />
              </label>
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm font-semibold text-gray-500">
                {selectedEventId
                  ? `${getTypeLabel(form)} - ${optionLabel(STATUSES, form.status)}`
                  : ''}
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {selectedEventId && canEdit && (
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={saving}
                    className="h-10 rounded-md bg-red-600 px-4 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-60"
                  >
                    Supprimer
                  </button>
                )}
                {canEdit && (
                  <button
                    type="submit"
                    disabled={saving}
                    className="h-10 rounded-md bg-blue-600 px-5 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-60"
                  >
                    {saving ? 'Sauvegarde...' : 'Sauvegarder'}
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

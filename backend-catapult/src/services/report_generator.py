import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Wedge
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import base64


class SessionReportGenerator:
    """Generate professional training session reports with gauges and tables"""
    
    # Color scheme matching the example
    COLORS = {
        'background': '#1a2332',
        'header_bg': '#0d1620',
        'gauge_bg': '#2d3748',
        'gauge_fill': '#4a5568',
        'text_white': '#ffffff',
        'text_gray': '#a0aec0',
        'pink': '#f687b3',
        'green': '#48bb78',
        'light_green': '#68d391',
        'yellow': '#ecc94b',
        'orange': '#ed8936',
        'red': '#f56565',
        'dark_green': '#2f855a',
        'dark_orange': '#c05621',
        'dark_red': '#c53030',
    }
    
    @staticmethod
    def excel_date_to_datetime(excel_date: str) -> datetime:
        """
        Convert Excel serial date to Python datetime
        
        Args:
            excel_date: Excel serial date as string (e.g., "45981")
            
        Returns:
            datetime object
        """
        try:
            # Excel epoch starts on 1900-01-01 (with bug that 1900 is leap year)
            excel_epoch = datetime(1899, 12, 30)
            days = float(excel_date)
            return excel_epoch + timedelta(days=days)
        except:
            return datetime.now()
    
    @staticmethod
    def extract_session_metadata(session_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract metadata from session data
        
        Args:
            session_data: List of player sessions
            
        Returns:
            Dictionary with date, week, match info
        """
        if not session_data:
            return {
                'date': datetime.now().strftime('%d/%m/%Y'),
                'week': str(datetime.now().isocalendar()[1]),
                'match': '-'
            }
        
        first_session = session_data[0]
        
        # Extract and convert date
        date_str = first_session.get('date', '')
        if date_str.isdigit():
            # Excel date format
            date_obj = SessionReportGenerator.excel_date_to_datetime(date_str)
        else:
            # Try to parse regular date
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                date_obj = datetime.now()
        
        # Calculate week number
        week_num = date_obj.isocalendar()[1]
        
        # Extract match/training info from tags
        tags = first_session.get('tags', '').lower()
        if 'match' in tags or 'game' in tags:
            # Try to extract opponent from session title
            session_title = first_session.get('session_title', '')
            match_info = 'MATCH'
        elif 'training' in tags or 'entrainement' in tags:
            match_info = 'ENTRAINEMENT'
        else:
            match_info = '-'
        
        return {
            'date': date_obj.strftime('%d/%m/%Y'),
            'week': str(week_num),
            'match': match_info
        }
    
    @staticmethod
    def calculate_benchmarks(all_sessions: List[Dict[str, Any]], months: int = 3) -> Dict[str, float]:
        """
        Calculate benchmark values from best sessions in last N months
        
        Args:
            all_sessions: All sessions from database
            months: Number of months to look back (default: 3)
            
        Returns:
            Dictionary with benchmark values for each metric
        """
        if not all_sessions:
            return {
                'distance_km': 100.0,
                'hsr_total': 5000.0,
                'dec_total': 100.0,
                'power_plays': 200.0,
            }
        
        # Filter sessions from last N months
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        # Filtrer les 3 derniers mois
        recent_sessions = [
            s for s in all_sessions
            if datetime.strptime(s.get('date', '2000-01-01'), '%Y-%m-%d') >= cutoff_date
        ]
        if not recent_sessions:
            recent_sessions = all_sessions  # fallback si pas assez de données

        # Grouper par session_title, calculer la moyenne par joueur (pour comparer
        # des séances avec des effectifs différents)
        session_totals = {}
        for session in recent_sessions:
            title = session.get('session_title', '')
            if title not in session_totals:
                session_totals[title] = {
                    'distance_km': 0,
                    'hsr_total': 0,
                    'power_plays': 0,
                    'decel_high_count': 0,
                    'player_count': 0,
                }
            session_totals[title]['distance_km'] += session.get('distance_km', 0)
            hsr = (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            session_totals[title]['hsr_total'] += hsr
            session_totals[title]['power_plays'] += session.get('power_plays', 0)
            session_totals[title]['decel_high_count'] += session.get('decel_high_count', 0)
            session_totals[title]['player_count'] += 1

        # Max de la MOYENNE par joueur → comparable quelle que soit la taille de l'effectif
        avgs = []
        for t in session_totals.values():
            if t['player_count'] < 6:
                continue
            n = t['player_count']
            avgs.append({
                'distance_km': t['distance_km'] / n,
                'hsr_total': t['hsr_total'] / n,
                'dec_total': t['decel_high_count'] / n,
                'power_plays': t['power_plays'] / n,
            })

        benchmarks = {
            'distance_km': max([a['distance_km'] for a in avgs]) if avgs else 100.0,
            'hsr_total': max([a['hsr_total'] for a in avgs]) if avgs else 5000.0,
            'dec_total': max([a['dec_total'] for a in avgs]) if avgs else 100.0,
            'power_plays': max([a['power_plays'] for a in avgs]) if avgs else 200.0,
        }
        
        return benchmarks
    
    @staticmethod
    def calculate_personal_max_by_player(all_sessions: List[Dict[str, Any]], reference_date: datetime = None) -> Dict[str, Dict[str, float]]:
        """
        Calculate personal maximum values for each player across all their sessions
        Limited to the current season (from July 1st of the reference year).
        
        Args:
            all_sessions: All sessions from database
            reference_date: Date of the session being reported (filters to current season)
            
        Returns:
            Dictionary with player_name as key and their personal max values
        """
        if not all_sessions:
            return {}

        # Filter to current season (from August 1st of the reference year up to reference_date)
        if reference_date is not None:
            ref = reference_date if isinstance(reference_date, datetime) else datetime.combine(reference_date, datetime.min.time())
            season_year = ref.year if ref.month >= 8 else ref.year - 1
            season_start = datetime(season_year, 8, 1)
            def _in_season(s):
                if s.get('split_name', '') != 'all':
                    return False
                sd = s.get('session_date')
                if sd is None:
                    return False
                d = sd if isinstance(sd, datetime) else datetime.combine(sd, datetime.min.time())
                return season_start <= d <= ref
            all_sessions = [s for s in all_sessions if _in_season(s)]

        # Group by player and calculate their personal max
        player_max = {}
        
        for session in all_sessions:
            player = session.get('player_name', 'Unknown')
            if player not in player_max:
                player_max[player] = {
                    'max_distance_km': 0,
                    'max_hsr': 0,
                    'max_sprint': 0,
                    'max_top_speed': 0,
                    'max_decel_high': 0,
                    'max_power_plays': 0,
                    'max_duration': 0,
                    'max_accel_count': 0,
                    'max_decel_count': 0,
                    'max_z3_secs': 0,
                    'max_z4_secs': 0,
                    'max_z5_secs': 0,
                    'max_z345': 0,   # max(z3+z4+z5) per session
                    'max_z45': 0,    # max(z4+z5) per session
                    'max_temps_ad_secs': 0,
                }
            
            # Update max values if current session is higher
            player_max[player]['max_distance_km'] = max(
                player_max[player]['max_distance_km'],
                session.get('distance_km', 0)
            )
            # Calculate HSR from speed zones for max tracking
            session_hsr = (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            player_max[player]['max_hsr'] = max(
                player_max[player]['max_hsr'],
                session_hsr
            )
            player_max[player]['max_decel_high'] = max(
                player_max[player]['max_decel_high'],
                session.get('decel_high_count', 0)
            )
            player_max[player]['max_power_plays'] = max(
                player_max[player]['max_power_plays'],
                session.get('power_plays', 0)
            )
            player_max[player]['max_sprint'] = max(
                player_max[player]['max_sprint'],
                session.get('sprint_distance_m', 0)
            )
            player_max[player]['max_top_speed'] = max(
                player_max[player]['max_top_speed'],
                session.get('top_speed', 0)
            )
            # Cap at 10000s (167 min) to exclude GPS-left-on artifacts
            # (match sessions often show 3-4h of total GPS recording instead of ~90 min)
            if session.get('duration', 0) <= 10000:
                player_max[player]['max_duration'] = max(
                    player_max[player]['max_duration'],
                    session.get('duration', 0)
                )
            player_max[player]['max_accel_count'] = max(
                player_max[player]['max_accel_count'], session.get('accel_count', 0)
            )
            player_max[player]['max_decel_count'] = max(
                player_max[player]['max_decel_count'], session.get('decel_count', 0)
            )
            player_max[player]['max_z3_secs'] = max(player_max[player]['max_z3_secs'], session.get('speed_zone_3_secs', 0))
            player_max[player]['max_z4_secs'] = max(player_max[player]['max_z4_secs'], session.get('speed_zone_4_secs', 0))
            player_max[player]['max_z5_secs'] = max(player_max[player]['max_z5_secs'], session.get('speed_zone_5_secs', 0))
            # Combined max per session (physically correct: from the same session)
            session_z345 = session.get('speed_zone_3_secs', 0) + session.get('speed_zone_4_secs', 0) + session.get('speed_zone_5_secs', 0)
            session_z45  = session.get('speed_zone_4_secs', 0) + session.get('speed_zone_5_secs', 0)
            player_max[player]['max_z345'] = max(player_max[player]['max_z345'], session_z345)
            player_max[player]['max_z45']  = max(player_max[player]['max_z45'],  session_z45)
            player_max[player]['max_temps_ad_secs'] = max(
                player_max[player]['max_temps_ad_secs'],
                session.get('temps_ad_secs', 0)
            )

        # Second pass: compute max weekly average per player (used by weekly report % columns)
        # Group sessions by (player, iso_week)
        from collections import defaultdict
        player_weeks: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: {
            'distance_km': 0, 'hsr': 0, 'sprint': 0,
            'decel_high_count': 0, 'power_plays': 0, 'dates': set()
        }))
        for session in all_sessions:
            player = session.get('player_name', 'Unknown')
            if player not in player_max:
                continue
            sd = session.get('session_date')
            if sd is None:
                continue
            d = sd if isinstance(sd, datetime) else datetime.combine(sd, datetime.min.time())
            wk = f"{d.year}-W{d.isocalendar()[1]:02d}"
            pw = player_weeks[player][wk]
            pw['distance_km'] += session.get('distance_km', 0)
            pw['hsr'] += (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            pw['sprint'] += session.get('sprint_distance_m', 0)
            pw['decel_high_count'] += session.get('decel_high_count', 0)
            pw['power_plays'] += session.get('power_plays', 0)
            pw['dates'].add(str(d.date()))

        for player, weeks in player_weeks.items():
            max_wk_dist = max_wk_hsr = max_wk_sprint = max_wk_imp = max_wk_pp = 0.0
            for wk, data in weeks.items():
                n = len(data['dates']) or 1
                max_wk_dist   = max(max_wk_dist,   data['distance_km'] / n)
                max_wk_hsr    = max(max_wk_hsr,    data['hsr']         / n)
                max_wk_sprint = max(max_wk_sprint,  data['sprint']      / n)
                max_wk_imp    = max(max_wk_imp,     data['decel_high_count'] / n)
                max_wk_pp     = max(max_wk_pp,      data['power_plays'] / n)
            player_max[player]['max_weekly_avg_distance_km'] = max_wk_dist
            player_max[player]['max_weekly_avg_hsr']         = max_wk_hsr
            player_max[player]['max_weekly_avg_sprint']      = max_wk_sprint
            player_max[player]['max_weekly_avg_impacts']     = max_wk_imp
            player_max[player]['max_weekly_avg_pp']          = max_wk_pp

        return player_max

    @staticmethod
    def draw_semi_gauge(ax, value: float, max_value: float, title: str, percentage: float, fmt: str = 'd'):
        """
        Draw a semi-circular gauge
        
        Args:
            ax: Matplotlib axis
            value: Current value
            max_value: Maximum value for the gauge
            title: Title above the gauge
            percentage: Percentage to display
        """
        # Background arc (gray)
        wedge_bg = Wedge(
            (0.5, 0), 0.4, 0, 180,
            width=0.12,
            facecolor=SessionReportGenerator.COLORS['gauge_bg'],
            edgecolor='none'
        )
        ax.add_patch(wedge_bg)
        
        # Value arc (darker gray) - fills from left (180°) to right (0°)
        angle = 180 * (value / max_value) if max_value > 0 else 0
        wedge_fill = Wedge(
            (0.5, 0), 0.4, 180 - angle, 180,
            width=0.12,
            facecolor=SessionReportGenerator.COLORS['gauge_fill'],
            edgecolor='none'
        )
        ax.add_patch(wedge_fill)
        
        # Center value
        ax.text(0.5, 0.15, format(value, fmt) if fmt != 'd' else str(int(value)), 
                ha='center', va='center',
                fontsize=24, fontweight='bold',
                color=SessionReportGenerator.COLORS['text_white'])
        
        # Title above
        ax.text(0.5, 0.75, title,
                ha='center', va='center',
                fontsize=10, fontweight='bold',
                color=SessionReportGenerator.COLORS['text_white'])
        
        # Percentage on the right
        ax.text(0.95, 0.5, f'{int(percentage)}%',
                ha='center', va='center',
                fontsize=20, fontweight='bold',
                color=SessionReportGenerator.COLORS['text_white'])
        
        # Min/Max labels
        ax.text(0.1, -0.05, '0',
                ha='center', va='top',
                fontsize=8,
                color=SessionReportGenerator.COLORS['text_gray'])
        ax.text(0.9, -0.05, format(max_value, fmt) if fmt != 'd' else str(int(max_value)),
                ha='center', va='top',
                fontsize=8,
                color=SessionReportGenerator.COLORS['text_gray'])
        
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.1, 0.9)
        ax.axis('off')
    
    @staticmethod
    def get_color_for_pct(value: float) -> str:
        """
        Get background color based on fixed percentage thresholds:
          0-20  -> dark red
          21-40 -> orange
          41-60 -> yellow
          61-80 -> light green
          81+   -> dark green
        """
        if value > 80:
            return SessionReportGenerator.COLORS['dark_green']
        elif value > 60:
            return SessionReportGenerator.COLORS['light_green']
        elif value > 40:
            return SessionReportGenerator.COLORS['yellow']
        elif value > 20:
            return SessionReportGenerator.COLORS['orange']
        else:
            return SessionReportGenerator.COLORS['dark_red']
    
    @staticmethod
    def generate_session_report(
        session_data: List[Dict[str, Any]],
        all_sessions: List[Dict[str, Any]],
        session_title: str,
        raw_rows: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate complete session report with automatic metadata extraction
        
        Args:
            session_data: List of player sessions for this specific session
            all_sessions: All sessions in database (for benchmarks)
            session_title: Title of the session
            
        Returns:
            Base64-encoded PNG image
        """
        # Extract metadata automatically
        metadata = SessionReportGenerator.extract_session_metadata(session_data)
        date = metadata['date']
        week = metadata['week']
        match = metadata['match']
        # Create figure with dark background
        fig = plt.figure(figsize=(20, 14), facecolor=SessionReportGenerator.COLORS['background'])
        
        # Calculer la MOYENNE par joueur (comparable quelle que soit la taille de l'effectif)
        nb_players = len(session_data) or 1
        total_distance = sum(s.get('distance_km', 0) for s in session_data) / nb_players
        total_hsr = sum((s.get('speed_zone_3_km', 0) + s.get('speed_zone_4_km', 0) + s.get('speed_zone_5_km', 0)) * 1000 for s in session_data) / nb_players
        total_dec = sum(s.get('decel_high_count', 0) for s in session_data) / nb_players
        total_pp = sum(s.get('power_plays', 0) for s in session_data) / nb_players
        
        # Get benchmarks
        benchmarks = SessionReportGenerator.calculate_benchmarks(all_sessions)
        # Reference date from session for season-scoped personal maxes
        _ref_date = None
        if session_data:
            _d = session_data[0].get('session_date')
            if _d:
                _ref_date = datetime.combine(_d, datetime.min.time()) if not isinstance(_d, datetime) else _d
        personal_max_by_player = SessionReportGenerator.calculate_personal_max_by_player(all_sessions, reference_date=_ref_date)

        # Build sprint_by_player from raw_rows (sum sprint_distance_m where split_name == 0)
        sprint_by_player = {}
        if raw_rows:
            for r in raw_rows:
                player = r.get('player_name', 'Unknown')
                split = str(r.get('split_name') or '').strip().lower()
                is_zero = False
                try:
                    if split != '':
                        if float(split) == 0:
                            is_zero = True
                except:
                    is_zero = (split == '0' or split == 'zero')
                if is_zero:
                    sprint_by_player[player] = sprint_by_player.get(player, 0) + (r.get('sprint_distance_m') or 0)

        # Calculate percentages

        pct_distance = (total_distance / benchmarks['distance_km'] * 100) if benchmarks['distance_km'] > 0 else 0
        pct_hsr = (total_hsr / benchmarks['hsr_total'] * 100) if benchmarks['hsr_total'] > 0 else 0
        pct_dec = (total_dec / benchmarks['dec_total'] * 100) if benchmarks['dec_total'] > 0 else 0
        pct_pp = (total_pp / benchmarks['power_plays'] * 100) if benchmarks['power_plays'] > 0 else 0
        
        # === HEADER ===
        header_ax = plt.axes([0.05, 0.83, 0.9, 0.15])
        header_ax.set_facecolor('#ffffff')
        
        # Add white rectangle to ensure background is visible
        rect = patches.Rectangle((0, 0), 1, 1, linewidth=0, 
                                edgecolor='none', facecolor='#ffffff', zorder=0)
        header_ax.add_patch(rect)
        
        # Logo on the left
        try:
            logo_path = 'assets/logo.png'
            logo = Image.open(logo_path)
            # Place logo within header_ax coordinates (0-1)
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            imagebox = OffsetImage(logo, zoom=0.25)
            ab = AnnotationBbox(imagebox, (0.12, 0.5), frameon=False, 
                              xycoords='axes fraction', box_alignment=(0.5, 0.5))
            header_ax.add_artist(ab)
        except:
            pass  # Logo optional
        
        # Title
        header_ax.text(0.5, 0.5, 'RAPPORT DE SÉANCE',
                      ha='center', va='center',
                      fontsize=28, fontweight='bold',
                      color='#1a2332', zorder=10)
        
        # Date, Week, Match boxes
        info_y = 0.5
        header_ax.text(0.7, info_y + 0.15, 'DATE',
                      ha='center', va='center', fontsize=9,
                      color='#718096', zorder=10)
        header_ax.text(0.7, info_y - 0.15, date,
                      ha='center', va='center', fontsize=11, fontweight='bold',
                      color='#1a2332', zorder=10)
        
        header_ax.text(0.8, info_y + 0.15, 'SEMAINE',
                      ha='center', va='center', fontsize=9,
                      color='#718096', zorder=10)
        header_ax.text(0.8, info_y - 0.15, week,
                      ha='center', va='center', fontsize=11, fontweight='bold',
                      color='#1a2332', zorder=10)
        
        header_ax.text(0.9, info_y + 0.15, 'TYPE',
                      ha='center', va='center', fontsize=9,
                      color='#718096', zorder=10)
        header_ax.text(0.9, info_y - 0.15, match,
                      ha='center', va='center', fontsize=11, fontweight='bold',
                      color='#1a2332', zorder=10)
        
        header_ax.set_xlim(0, 1)
        header_ax.set_ylim(0, 1)
        header_ax.axis('off')
        
        # === GAUGES ===
        gauge_y = 0.62
        gauge_height = 0.14
        gauge_width = 0.2
        
        # Distance gauge
        ax1 = plt.axes([0.05, gauge_y, gauge_width, gauge_height])
        SessionReportGenerator.draw_semi_gauge(
            ax1, total_distance, benchmarks['distance_km'],
            'DISTANCE ÉQUIPE', pct_distance, fmt='.2f'
        )
        
        # HSR gauge
        ax2 = plt.axes([0.28, gauge_y, gauge_width, gauge_height])
        SessionReportGenerator.draw_semi_gauge(
            ax2, total_hsr, benchmarks['hsr_total'],
            'HSR ÉQUIPE', pct_hsr
        )
        
        # DEC gauge
        ax3 = plt.axes([0.51, gauge_y, gauge_width, gauge_height])
        SessionReportGenerator.draw_semi_gauge(
            ax3, total_dec, benchmarks['dec_total'],
            'DEC ÉQUIPE', pct_dec
        )
        
        # Power Play gauge
        ax4 = plt.axes([0.74, gauge_y, gauge_width, gauge_height])
        SessionReportGenerator.draw_semi_gauge(
            ax4, total_pp, benchmarks['power_plays'],
            'POWER PLAY', pct_pp
        )
        
        # === TABLE ===
        table_ax = plt.axes([0.0, 0.05, 1.0, 0.54])
        table_ax.set_facecolor(SessionReportGenerator.COLORS['background'])
        table_ax.axis('off')
        
        # Pre-compute per-player % values and VOL/INT needed for percentile thresholds
        _precomp = {}
        for _p in session_data:
            _name = _p.get('player_name', 'Unknown')
            _pm = personal_max_by_player.get(_name, {})
            _dist   = _p.get('distance_km', 0)
            _hsr    = (_p.get('speed_zone_3_km', 0) + _p.get('speed_zone_4_km', 0) + _p.get('speed_zone_5_km', 0)) * 1000
            _sprint = sprint_by_player.get(_name, _p.get('sprint_distance_m', _hsr))
            _dec    = _p.get('decel_high_count', 0)
            _pp_val = _p.get('power_plays', 0)
            _pct_dist   = (_dist   / _pm['max_distance_km']  * 100) if _pm.get('max_distance_km', 0)  > 0 else 0
            _pct_hsr    = (_hsr    / _pm['max_hsr']          * 100) if _pm.get('max_hsr', 0)          > 0 else 0
            _pct_sprint = (_sprint / _pm['max_sprint']       * 100) if _pm.get('max_sprint', 0)       > 0 else 0
            _pct_dec    = (_dec    / _pm['max_decel_high']   * 100) if _pm.get('max_decel_high', 0)   > 0 else 0
            _pct_pp     = (_pp_val / _pm['max_power_plays']  * 100) if _pm.get('max_power_plays', 0)  > 0 else 0
            _max_ad = _pm.get('max_accel_count', 0) + _pm.get('max_decel_count', 0)
            _ad     = _p.get('accel_count', 0) + _p.get('decel_count', 0)
            _vol = int(((
                (_dist   / _pm['max_distance_km'] if _pm.get('max_distance_km', 0) > 0 else 0) +
                (_hsr    / _pm['max_hsr']          if _pm.get('max_hsr', 0)         > 0 else 0) +
                (_sprint / _pm['max_sprint']       if _pm.get('max_sprint', 0)      > 0 else 0) +
                (_ad     / _max_ad                 if _max_ad > 0 else 0)
            ) / 4) * 100)
            _dur   = _p.get('duration', 0)
            _z345  = _p.get('speed_zone_3_secs', 0) + _p.get('speed_zone_4_secs', 0) + _p.get('speed_zone_5_secs', 0)
            _z45   = _p.get('speed_zone_4_secs', 0) + _p.get('speed_zone_5_secs', 0)
            _tad   = _p.get('temps_ad_secs', 0)
            _int = int(((
                (_dur  / _pm['max_duration']      if _pm.get('max_duration', 0)      > 0 else 0) +
                (_z345 / _pm.get('max_z345', 0)   if _pm.get('max_z345', 0)          > 0 else 0) +
                (_z45  / _pm.get('max_z45', 0)    if _pm.get('max_z45', 0)           > 0 else 0) +
                (_tad  / _pm['max_temps_ad_secs'] if _pm.get('max_temps_ad_secs', 0) > 0 else 0)
            ) / 4) * 100)
            _precomp[_name] = {
                'pct_dist': _pct_dist, 'pct_hsr': _pct_hsr, 'pct_sprint': _pct_sprint,
                'pct_dec': _pct_dec, 'pct_pp': _pct_pp, 'vol': _vol, 'int': _int
            }

        # Colors are based on fixed % thresholds, no percentile computation needed
        
        # Column headers
        headers = ['JOUEUR', 'MINUTES', 'DISTANCE', '%DIST', 'HSR', '%HSR', 
                  'SPRINT', '%SPRINT', 'VMAX', 'DEC', '%DEC', 'PP', '%PP', 'M/MIN', 'VOL', 'INT']
        
        num_cols = len(headers)
        num_rows = len(session_data) + 1  # +1 for header
        
                # Largeurs personnalisées (total = 1.0)
        # Largeurs relatives (normalisées à 1.0)
        widths_raw = [16, 5.5, 6.5, 5, 5.5, 5, 5.5, 5.5, 5, 5.5, 5, 5, 5, 5.5, 5, 5.5]
        col_widths = [w/sum(widths_raw) for w in widths_raw]
        row_height = 1.0 / num_rows
        
        # Draw header row
        for col_idx, header in enumerate(headers):
            x = sum(col_widths[:col_idx])  # Position cumulative
            current_width = col_widths[col_idx]
            y = 1 - row_height
            
            rect = patches.Rectangle(
                (x, y), current_width, row_height,
                linewidth=0.5, edgecolor='white',
                facecolor=SessionReportGenerator.COLORS['header_bg']
            )
            table_ax.add_patch(rect)
            
            table_ax.text(
                x + current_width/2, y + row_height/2, header,
                ha='center', va='center',
                fontsize=8, fontweight='bold',
                color=SessionReportGenerator.COLORS['text_white']
            )
        
        # Draw data rows
        sorted_session_data = sorted(session_data, key=lambda p: p.get('player_name', ''))
        for row_idx, player in enumerate(sorted_session_data):
            y = 1 - (row_idx + 2) * row_height
            
            # Calculate player stats
            duration_min = player.get('duration', 0) / 60
            distance = player.get('distance_km', 0)
            hsr = (player.get('speed_zone_3_km', 0) + player.get('speed_zone_4_km', 0) + player.get('speed_zone_5_km', 0)) * 1000
            sprint = sprint_by_player.get(player.get('player_name', 'Unknown'), player.get('sprint_distance_m', hsr))
            vmax = player.get('top_speed', 0) * 3.6  # m/s → km/h
            dec = player.get('decel_high_count', 0)
            pp = player.get('power_plays', 0)
            dist_per_min = player.get('distance_per_min', 0)
            player_load = player.get('player_load', 0)
            
            # Calculate percentages
            # Get personal max for this player
            player_name = player.get('player_name', 'Unknown')
            personal_max = personal_max_by_player.get(player_name, {})
            pct_dist = (distance / personal_max.get('max_distance_km', 1) * 100) if personal_max.get('max_distance_km', 0) > 0 else 0
            pct_hsr = (hsr / personal_max.get('max_hsr', 1) * 100) if personal_max.get('max_hsr', 0) > 0 else 0
            pct_sprint = (sprint / personal_max.get('max_sprint', 1) * 100) if personal_max.get('max_sprint', 0) > 0 else 0
            pct_dec = (dec / personal_max.get('max_decel_high', 1) * 100) if personal_max.get('max_decel_high', 0) > 0 else 0
            pct_pp = (pp / personal_max.get('max_power_plays', 1) * 100) if personal_max.get('max_power_plays', 0) > 0 else 0

            # VOL = moyenne de 4 ratios personnels : dist, HSR, sprint, (DEC+ACC counts)
            # dénominateur = max_DEC + max_ACC (somme des maxes séparés, comme Excel)
            max_ad_denom = personal_max.get('max_accel_count', 0) + personal_max.get('max_decel_count', 0)
            ad_count     = player.get('accel_count', 0) + player.get('decel_count', 0)
            r_dist   = (distance / personal_max['max_distance_km']) if personal_max.get('max_distance_km', 0) > 0 else 0
            r_hsr    = (hsr / personal_max['max_hsr'])               if personal_max.get('max_hsr', 0) > 0 else 0
            r_sprint = (sprint / personal_max['max_sprint'])         if personal_max.get('max_sprint', 0) > 0 else 0
            r_ad     = (ad_count / max_ad_denom)                     if max_ad_denom > 0 else 0
            vol_pct  = int((r_dist + r_hsr + r_sprint + r_ad) / 4 * 100)

            # INT = moyenne de 4 ratios personnels : duration, z345_secs, z45_secs, temps_ad
            # dénominateurs = max(z3+z4+z5) et max(z4+z5) par session individuelle (valeur combinée max)
            duration_s   = player.get('duration', 0)
            z345_val     = player.get('speed_zone_3_secs', 0) + player.get('speed_zone_4_secs', 0) + player.get('speed_zone_5_secs', 0)
            z45_val      = player.get('speed_zone_4_secs', 0) + player.get('speed_zone_5_secs', 0)
            temps_ad     = player.get('temps_ad_secs', 0)
            max_z345_den = personal_max.get('max_z345', 0)
            max_z45_den  = personal_max.get('max_z45', 0)
            r_dur  = (duration_s / personal_max['max_duration'])   if personal_max.get('max_duration', 0) > 0 else 0
            r_z345 = (z345_val / max_z345_den)                     if max_z345_den > 0 else 0
            r_z45  = (z45_val  / max_z45_den)                      if max_z45_den  > 0 else 0
            r_tad  = (temps_ad / personal_max['max_temps_ad_secs']) if personal_max.get('max_temps_ad_secs', 0) > 0 else 0
            int_pct = int((r_dur + r_z345 + r_z45 + r_tad) / 4 * 100)
            
            # Row data
            row_data = [
                player.get('player_name', 'Unknown'),
                f"{int(duration_min)}",
                f"{distance:.2f}",
                f"{int(pct_dist)}%",
                f"{int(hsr)}",
                f"{int(pct_hsr)}%",
                f"{int(sprint)}",
                f"{int(pct_sprint)}%",
                f"{vmax:.2f}",
                f"{int(dec)}",
                f"{int(pct_dec)}%",
                f"{int(pp)}",
                f"{int(pct_pp)}%",
                f"{dist_per_min:.2f}",
                f"{vol_pct}%",
                f"{int_pct}%"
            ]
            
            # Determine colors for specific columns (fixed % thresholds)
            _pc = _precomp.get(player_name, {})
            colors = [SessionReportGenerator.COLORS['background']] * num_cols
            colors[3]  = SessionReportGenerator.get_color_for_pct(_pc.get('pct_dist',   0))
            colors[5]  = SessionReportGenerator.get_color_for_pct(_pc.get('pct_hsr',    0))
            colors[7]  = SessionReportGenerator.get_color_for_pct(_pc.get('pct_sprint', 0))
            colors[10] = SessionReportGenerator.get_color_for_pct(_pc.get('pct_dec',    0))
            colors[12] = SessionReportGenerator.get_color_for_pct(_pc.get('pct_pp',     0))
            colors[14] = SessionReportGenerator.get_color_for_pct(_pc.get('vol',        0))
            colors[15] = SessionReportGenerator.get_color_for_pct(_pc.get('int',        0))
            
            for col_idx, (value, bg_color) in enumerate(zip(row_data, colors)):
                x = sum(col_widths[:col_idx])  # Position cumulative
                current_width = col_widths[col_idx]
                
                rect = patches.Rectangle(
                    (x, y), current_width, row_height,
                    linewidth=0.5, edgecolor='#4a5568',
                    facecolor=bg_color
                )
                table_ax.add_patch(rect)
                
                # Text alignment
                alignment = 'left' if col_idx == 0 else 'center'
                x_text = x + 0.01 if col_idx == 0 else x + current_width/2
                cell_text_color = '#000000' if bg_color != SessionReportGenerator.COLORS['background'] else SessionReportGenerator.COLORS['text_white']
                
                table_ax.text(
                    x_text, y + row_height/2, value,
                    ha=alignment, va='center',
                    fontsize=7,
                    color=cell_text_color
                )
        
        table_ax.set_xlim(0, 1)
        table_ax.set_ylim(0, 1)
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor=SessionReportGenerator.COLORS['background'])
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        plt.close(fig)
        
        return img_base64


class WeeklyReportGenerator:
    """Generate weekly training reports with daily breakdown and trends"""
    
    COLORS = SessionReportGenerator.COLORS

    @staticmethod
    def calculate_weekly_benchmarks(all_sessions):
        """
        Calculate maximum values per week across all historical sessions.
        Returns max per session (average) for fair comparison.
        
        Returns dict with max values in same units as calculate_benchmarks():
        - distance_km: max average distance per session in a week (km)
        - hsr_total: max average HSR per session in a week (meters)
        - dec_total: max average impacts per session in a week
        - power_plays: max average power plays per session in a week
        """
        from datetime import datetime
        from collections import defaultdict
        
        # Group sessions by ISO week
        weekly_data = defaultdict(lambda: {
            'distance_km': 0,
            'sprint_distance_m': 0,
            'actual_sprint_m': 0,
            'impacts': 0,
            'decel_high_count': 0,
            'power_plays': 0,
            'session_count': 0,
            'dates': set()
        })
        
        for session in all_sessions:
            # Get ISO week number
            session_date = datetime.fromisoformat(str(session.get('session_date', session.get('date'))))
            year, week, _ = session_date.isocalendar()
            week_key = f"{year}-W{week:02d}"
            
            # Get date string for counting unique sessions
            date_str = session_date.strftime('%Y-%m-%d')
            
            # Add totals — HSR from speed zones 3+4+5 (consistent with session report)
            session_hsr = (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            weekly_data[week_key]['distance_km']      += session.get('distance_km', 0)
            weekly_data[week_key]['sprint_distance_m'] += session_hsr
            weekly_data[week_key]['actual_sprint_m']   += session.get('sprint_distance_m', 0)
            weekly_data[week_key]['impacts']           += session.get('impacts', 0)
            weekly_data[week_key]['decel_high_count']  += session.get('decel_high_count', 0)
            weekly_data[week_key]['power_plays']       += session.get('power_plays', 0)
            weekly_data[week_key]['dates'].add(date_str)
        
        # Calculate session count for each week (unique dates)
        for week_key in weekly_data:
            weekly_data[week_key]['session_count'] = len(weekly_data[week_key]['dates'])
        
        # Find max AVERAGE per session across all weeks
        max_avg_distance = 0
        max_avg_hsr = 0
        max_avg_sprint = 0
        max_avg_dec = 0
        max_avg_pp = 0
        
        for week_key, data in weekly_data.items():
            session_count = data['session_count']
            if session_count > 0:
                avg_dist   = data['distance_km']      / session_count
                avg_hsr    = data['sprint_distance_m'] / session_count
                avg_sprint = data['actual_sprint_m']  / session_count
                avg_dec    = data['decel_high_count']  / session_count
                avg_pp     = data['power_plays']       / session_count

                max_avg_distance = max(max_avg_distance, avg_dist)
                max_avg_hsr      = max(max_avg_hsr,      avg_hsr)
                max_avg_sprint   = max(max_avg_sprint,   avg_sprint)
                max_avg_dec      = max(max_avg_dec,      avg_dec)
                max_avg_pp       = max(max_avg_pp,       avg_pp)
        
        return {
            'distance_km':  max_avg_distance,
            'hsr_total':    max_avg_hsr,
            'sprint_total': max_avg_sprint,
            'dec_total':    max_avg_dec,
            'power_plays':  max_avg_pp
        }

    
    @staticmethod
    def aggregate_by_player(session_data: List[Dict]) -> List[Dict]:
        """Agrège les données par joueur sur toute la semaine"""
        player_totals = {}
        
        for session in session_data:
            player = session['player_name']
            if player not in player_totals:
                player_totals[player] = {
                    'player_name': player,
                    'duration': 0,
                    'distance_km': 0,
                    'sprint_distance_m': 0,
                    'power_score': 0,
                    'decel_high_count': 0,
                    'power_plays': 0,
                    'top_speed': 0,
                    'session_count': 0,  # Track total sessions
                    'speed_zone_3_km': 0,
                    'speed_zone_4_km': 0,
                    'speed_zone_5_km': 0
                }
            
            player_totals[player]['duration'] += session.get('duration', 0)
            player_totals[player]['distance_km'] += session.get('distance_km', 0)
            player_totals[player]['sprint_distance_m'] += session.get('sprint_distance_m', 0)
            player_totals[player]['speed_zone_3_km'] += session.get('speed_zone_3_km', 0)
            player_totals[player]['speed_zone_4_km'] += session.get('speed_zone_4_km', 0)
            player_totals[player]['speed_zone_5_km'] += session.get('speed_zone_5_km', 0)
            player_totals[player]['power_score'] = max(player_totals[player]['power_score'], session.get('power_score', 0))
            player_totals[player]['decel_high_count'] += session.get('decel_high_count', 0)
            player_totals[player]['power_plays'] += session.get('power_plays', 0)
            player_totals[player]['top_speed'] = max(player_totals[player]['top_speed'], session.get('top_speed', 0))
            # Compter toutes les séances (y compris double séance le même jour)
            player_totals[player]['session_count'] += 1
        
        result = []
        for player_name, data in player_totals.items():
            result.append(data)
        
        return result
    
    @staticmethod
    def aggregate_by_day(session_data: List[Dict]) -> Dict[str, Dict]:
        """Agrège les données par jour de la semaine.
        Si un jour a deux séances (matin/après-midi détectées dans le titre),
        elles sont retournées sous des clés séparées : 'MARDI MA' et 'MARDI AP'.
        """
        from collections import defaultdict
        from datetime import datetime

        DAY_NAMES = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

        def get_slot(title: str) -> str:
            """Retourne 'MA' (matin) ou 'AP' (après-midi) ou '' selon le titre.
            Convention PSG : AM = Après Midi, MATIN = matin.
            """
            t = str(title).upper()
            # Matin
            if 'MATIN' in t:
                return 'MA'
            # Après-midi : AM (convention PSG), APRES MIDI, PM, etc.
            if any(kw in t for kw in ['AM', 'APRES MIDI', 'APRÈS MIDI', 'APRES-MIDI', 'APRÈS-MIDI', 'APREM', 'PM']):
                return 'AP'
            return ''

        # Regrouper les sessions par jour
        day_sessions = defaultdict(list)
        for session in session_data:
            date_str = session.get('date', '')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception:
                continue
            day_name = DAY_NAMES[date.weekday()]
            day_sessions[day_name].append(session)

        def _sum_sessions(sessions):
            totals = {
                'duration': 0, 'distance_km': 0.0, 'sprint_distance_m': 0.0,
                'speed_zone_3_km': 0.0, 'speed_zone_4_km': 0.0, 'speed_zone_5_km': 0.0,
                'impacts': 0, 'decel_high_count': 0, 'power_plays': 0, 'top_speed': 0.0,
                'player_count': set()
            }
            for s in sessions:
                totals['duration']           += s.get('duration', 0)
                totals['distance_km']        += s.get('distance_km', 0)
                totals['sprint_distance_m']  += s.get('sprint_distance_m', 0)
                totals['speed_zone_3_km']    += s.get('speed_zone_3_km', 0)
                totals['speed_zone_4_km']    += s.get('speed_zone_4_km', 0)
                totals['speed_zone_5_km']    += s.get('speed_zone_5_km', 0)
                totals['impacts']            += s.get('impacts', 0)
                totals['decel_high_count']   += s.get('decel_high_count', 0)
                totals['power_plays']        += s.get('power_plays', 0)
                totals['top_speed']           = max(totals['top_speed'], s.get('top_speed', 0))
                if s.get('player_name'):
                    totals['player_count'].add(s['player_name'])
            totals['player_count'] = len(totals['player_count'])
            return totals

        result = {}
        for day_name, sessions in day_sessions.items():
            slots = {get_slot(s.get('session_title', '')) for s in sessions}
            has_ma = 'MA' in slots
            has_ap = 'AP' in slots

            if has_ma or has_ap:
                # Séparer matin, après-midi et séances sans marqueur
                ma_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'MA']
                ap_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'AP']
                other = [s for s in sessions if get_slot(s.get('session_title', '')) == '']
                # Garder les séances sans tag séparément (poids, récup…)
                if other:
                    result[day_name] = _sum_sessions(other)
                if ma_sessions:
                    result[f'{day_name} MA'] = _sum_sessions(ma_sessions)
                if ap_sessions:
                    result[f'{day_name} AP'] = _sum_sessions(ap_sessions)
            else:
                result[day_name] = _sum_sessions(sessions)

        return result
    
    @staticmethod
    def generate_weekly_report(
        session_data: List[Dict[str, Any]],
        all_sessions: List[Dict[str, Any]],
        team_name: str,
        week_number: int,
        year: int
    ) -> str:
        """
        Génère un rapport hebdomadaire complet
        
        Returns:
            Base64 encoded PNG image
        """
        # Aggregate data
        player_data = WeeklyReportGenerator.aggregate_by_player(session_data)
        day_data = WeeklyReportGenerator.aggregate_by_day(session_data)
        
        # Calculate weekly_benchmarks and personal max
        weekly_benchmarks = WeeklyReportGenerator.calculate_weekly_benchmarks(all_sessions)
        # Reference date: last day of the week (year + week_number)
        _ref_date = datetime.fromisocalendar(year, week_number, 7)
        personal_max = SessionReportGenerator.calculate_personal_max_by_player(all_sessions, reference_date=_ref_date)
        
        # Create figure
        fig = plt.figure(figsize=(16, 20), facecolor=WeeklyReportGenerator.COLORS['background'])
        
        # === HEADER === (use plt.axes like session report)
        header_ax = plt.axes([0.05, 0.83, 0.9, 0.15])
        WeeklyReportGenerator._draw_header(header_ax, team_name, week_number, year, len(session_data))
        
        # === GAUGES === (below header)
        gauge_ax = plt.axes([0.05, 0.68, 0.9, 0.12])
        # Count unique session dates (not player-session rows)
        unique_dates = len(set(s.get('session_date', s.get('date', '')) for s in session_data))
        session_count = unique_dates if unique_dates > 0 else 1
        WeeklyReportGenerator._draw_gauges(gauge_ax, player_data, weekly_benchmarks, session_count)
        # === PLAYER TABLE === (main table)
        table_ax = plt.axes([0.05, 0.44, 0.9, 0.28])
        WeeklyReportGenerator._draw_player_table(table_ax, player_data, weekly_benchmarks, personal_max)

        # === DAILY TABLE === (pleine largeur)
        daily_table_ax = plt.axes([0.05, 0.22, 0.9, 0.21])
        WeeklyReportGenerator._draw_daily_table(daily_table_ax, day_data, weekly_benchmarks)

        # === TREND GRAPH === (pleine largeur, en dessous)
        graph_ax = plt.axes([0.05, 0.12, 0.9, 0.17])
        WeeklyReportGenerator._draw_trend_graph(graph_ax, day_data, weekly_benchmarks)

        # Save to bytes
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        
        # Convert to base64
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return img_base64
    
    @staticmethod
    def _draw_header(ax, team_name, week_number, year, session_count):
        """Draw header section - EXACT copy from session report"""
        from matplotlib import patches
        from PIL import Image
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        
        # Keep background transparent to show dark background
        ax.set_facecolor('none')
        
        # White rectangle starting after the logo (like session report style)
        rect = patches.Rectangle((0, 0.25), 0.99, 0.5, linewidth=1, 
                                edgecolor='none', facecolor='#ffffff', zorder=0)
        ax.add_patch(rect)
        
        # Logo on the left
        try:
            logo_path = 'assets/logo.png'
            logo = Image.open(logo_path)
            # Place logo within header_ax coordinates (0-1)
            imagebox = OffsetImage(logo, zoom=0.17)
            ab = AnnotationBbox(imagebox, (0.12, 0.5), frameon=False, 
                              xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab)
        except:
            pass  # Logo optional
        
        # Title
        ax.text(0.5, 0.5, 'RAPPORT HEBDOMADAIRE',
                ha='center', va='center',
                fontsize=20, fontweight='bold',
                color='#1a2332', zorder=10)
        
        # Info boxes (changed labels for weekly report)
        info_y = 0.5
        ax.text(0.75, info_y + 0.15, 'ÉQUIPE',
                ha='center', va='center', fontsize=9,
                color='#718096', zorder=10)
        ax.text(0.75, info_y - 0.15, team_name,
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='#1a2332', zorder=10)
        
        ax.text(0.85, info_y + 0.15, 'SEMAINE',
                ha='center', va='center', fontsize=9,
                color='#718096', zorder=10)
        ax.text(0.85, info_y - 0.15, str(week_number),
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='#1a2332', zorder=10)
        
        ax.text(0.95, info_y + 0.15, 'ANNÉE',
                ha='center', va='center', fontsize=9,
                color='#718096', zorder=10)
        ax.text(0.95, info_y - 0.15, str(year),
                ha='center', va='center', fontsize=11, fontweight='bold',
                color='#1a2332', zorder=10)
        
        # SÉANCES instead of TYPE (4th info box like session report has TYPE)
        # But we keep it at 0.9 position since we only have 3 boxes + 1 extra
        # Actually, looking at the image, session report only has 3 boxes
        # Let me add a 4th one for SÉANCES at the right position
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    
    @staticmethod
    def _draw_gauges(ax, player_data, benchmarks, session_count):
        """Draw the 4 gauges using SessionReportGenerator.draw_semi_gauge()"""
        # Calculate team totals (keep same units as benchmarks)
        total_distance = sum(p['distance_km'] for p in player_data)  # Keep in km
        # Calculate HSR from speed zones 3+4+5
        total_hsr = sum((p.get('speed_zone_3_km', 0) + p.get('speed_zone_4_km', 0) + p.get('speed_zone_5_km', 0)) * 1000 for p in player_data)
        total_impacts = sum(p.get('decel_high_count', 0) for p in player_data)
        total_power_plays = sum(p['power_plays'] for p in player_data)
        
        # Get benchmarks
        benchmark_distance = benchmarks.get('distance_km', 100)
        benchmark_hsr = benchmarks.get('hsr_total', 5000)
        benchmark_dec = benchmarks.get('dec_total', 100)
        benchmark_pp = benchmarks.get('power_plays', 200)
        
        # Calculate percentages
        # Calculate averages per session
        avg_distance = total_distance / session_count if session_count > 0 else 0
        avg_hsr = total_hsr / session_count if session_count > 0 else 0
        avg_impacts = total_impacts / session_count if session_count > 0 else 0
        avg_pp = total_power_plays / session_count if session_count > 0 else 0
        
        # Calculate percentages: (avg per session) / (max avg per session) * 100
        pct_distance = (avg_distance / benchmark_distance * 100) if benchmark_distance > 0 else 0
        pct_hsr = (avg_hsr / benchmark_hsr * 100) if benchmark_hsr > 0 else 0
        pct_dec = (avg_impacts / benchmark_dec * 100) if benchmark_dec > 0 else 0
        pct_pp = (avg_pp / benchmark_pp * 100) if benchmark_pp > 0 else 0
        
        # Draw 4 gauges using the same function as session report
        ax.axis('off')
        
        gauges = [
            ('DISTANCE ÉQUIPE', avg_distance, benchmark_distance, pct_distance, '.2f'),
            ('HSR ÉQUIPE', avg_hsr, benchmark_hsr, pct_hsr),
            ('DEC ÉQUIPE', avg_impacts, benchmark_dec, pct_dec),
            ('POWERPLAY ÉQUIPE', avg_pp, benchmark_pp, pct_pp)
        ]
        
        for i, gauge in enumerate(gauges):
            title, value, max_value, percentage = gauge[:4]
            fmt = gauge[4] if len(gauge) > 4 else 'd'
            # Create a sub-axis for each gauge
            gauge_ax = ax.inset_axes([i * 0.25, 0.3, 0.25, 1])
            # Use the same draw_semi_gauge function as session report
            SessionReportGenerator.draw_semi_gauge(gauge_ax, value, max_value, title, percentage, fmt=fmt)
    

    @staticmethod
    def _draw_player_table(ax, player_data, benchmarks, personal_max):
        """Draw complete player table with all columns and color coding"""
        ax.axis('off')
        ax.set_xlim(0, 15)
        ax.set_ylim(0, max(len(player_data) + 2, 10))
        
        # Colors based on fixed % thresholds — no percentile computation needed
        
        # Headers
        headers = ['JOUEUR', 'MINUTES', 'DISTANCE', '%DIST', 'HSR', '%HSR', 'SPRINT', '%SPRINT', 'VMAX', '%VMAX', 'DEC', '%DEC', 'POWER PLAY', '%PP', 'VOL', 'INT', 'NB SEANCES']
        col_widths = [2.5, 0.8, 0.8, 0.8, 0.9, 0.7, 0.9, 0.7, 0.7, 0.7, 0.7, 0.7, 0.9, 0.7, 0.7, 0.7, 0.9]
        
        x_pos = 0
        y = len(player_data) + 1
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            # Draw header cell background
            from matplotlib.patches import Rectangle
            rect = Rectangle((x_pos, y-0.4), width, 0.8,
                           facecolor=WeeklyReportGenerator.COLORS['header_bg'], 
                           edgecolor='white', linewidth=0.5)
            ax.add_patch(rect)
            
            ax.text(x_pos + width/2, y, header, ha='center', va='center',
                   fontsize=7, fontweight='bold', color=WeeklyReportGenerator.COLORS['text_white'])
            x_pos += width
        
        # Sort players by distance
        sorted_players = sorted(player_data, key=lambda p: p['player_name'])
        
        # Player rows
        for idx, player in enumerate(sorted_players):
            y -= 1
            minutes = player['duration'] // 60
            distance_m = int(player['distance_km'] * 1000)  # metres pour calcul %
            distance = player['distance_km']  # km pour affichage
            hsr = int((player.get('speed_zone_3_km', 0) + player.get('speed_zone_4_km', 0) + player.get('speed_zone_5_km', 0)) * 1000)
            sprint = int(player.get('sprint_distance_m', 0))
            impacts = player.get('decel_high_count', 0)
            pp = player['power_plays']
            vmax_raw = player['top_speed']  # m/s, pour calcul du %
            pmax = vmax_raw * 3.6  # m/s → km/h, pour affichage
            sessions = player['session_count']
            
            # Calculate percentages (simplified for now)
            # Get personal max for this player
            player_name = player['player_name']
            player_personal_max = personal_max.get(player_name, {})
            # Use max weekly average as denominator
            personal_max_dist    = player_personal_max.get('max_weekly_avg_distance_km', 1)  # km
            personal_max_hsr     = player_personal_max.get('max_weekly_avg_hsr', 1)
            personal_max_sprint  = player_personal_max.get('max_weekly_avg_sprint', 1)
            personal_max_impacts = player_personal_max.get('max_weekly_avg_impacts', 1)  # basé sur decel_high_count
            personal_max_pp      = player_personal_max.get('max_weekly_avg_pp', 1)

            # Average per session this week
            avg_dist_per_session    = distance_m / 1000 / sessions if sessions > 0 else 0  # km/séance
            avg_hsr_per_session     = hsr      / sessions if sessions > 0 else 0
            avg_sprint_per_session  = sprint   / sessions if sessions > 0 else 0
            avg_impacts_per_session = impacts  / sessions if sessions > 0 else 0
            avg_pp_per_session      = pp       / sessions if sessions > 0 else 0

            # % = (avg this week) / (best avg week historically) * 100
            dist_pct = int((avg_dist_per_session   / personal_max_dist)    * 100) if personal_max_dist    > 0 else 0
            hsr_pct  = int((avg_hsr_per_session    / personal_max_hsr)     * 100) if personal_max_hsr     > 0 else 0
            spr_pct  = int((avg_sprint_per_session / personal_max_sprint)  * 100) if personal_max_sprint  > 0 else 0
            personal_max_vmax = player_personal_max.get('max_top_speed', 0)
            pmax_pct = int((vmax_raw / personal_max_vmax) * 100) if personal_max_vmax > 0 else 0
            dec_pct = int((avg_impacts_per_session / personal_max_impacts) * 100) if personal_max_impacts > 0 else 0
            pp_pct = int((avg_pp_per_session / personal_max_pp) * 100) if personal_max_pp > 0 else 0
            
            # VOL = volume index : moyenne des 3 métriques de volume vs max hebdo personnel
            avg_distance_per_session = player['distance_km'] / sessions if sessions > 0 else 0
            vol_pct = int((dist_pct + hsr_pct + spr_pct) / 3)

            # INT = intensité : moyenne des 3 métriques d'intensité vs max hebdo personnel
            intensity_pct = int((hsr_pct + dec_pct + pp_pct) / 3)
            
            # Get colors based on fixed % thresholds
            row_data = [
                (player['player_name'][:20], None, 'center'),
                (str(minutes), None, 'center'),
                (f'{distance:.2f}', None, 'center'),
                (f'{dist_pct}%', SessionReportGenerator.get_color_for_pct(dist_pct), 'center'),
                (str(hsr), None, 'center'),
                (f'{hsr_pct}%', SessionReportGenerator.get_color_for_pct(hsr_pct), 'center'),
                (str(sprint), None, 'center'),
                (f'{spr_pct}%', SessionReportGenerator.get_color_for_pct(spr_pct), 'center'),
                (f'{pmax:.1f}', None, 'center'),
                (f'{pmax_pct}%', SessionReportGenerator.get_color_for_pct(pmax_pct), 'center'),
                (str(impacts), None, 'center'),
                (f'{dec_pct}%', SessionReportGenerator.get_color_for_pct(dec_pct), 'center'),
                (str(pp), None, 'center'),
                (f'{pp_pct}%', SessionReportGenerator.get_color_for_pct(pp_pct), 'center'),
                (f'{vol_pct}%', SessionReportGenerator.get_color_for_pct(vol_pct), 'center'),
                (f'{intensity_pct}%', SessionReportGenerator.get_color_for_pct(intensity_pct), 'center'),
                (str(sessions), None, 'center')
            ]
            
            x_pos = 0
            for (value, bgcolor, align), width in zip(row_data, col_widths):
                # Draw cell with border
                from matplotlib.patches import Rectangle
                if bgcolor:
                    rect = Rectangle((x_pos, y-0.4), width, 0.8, 
                                   facecolor=bgcolor, edgecolor='#4a5568', linewidth=0.5)
                else:
                    rect = Rectangle((x_pos, y-0.4), width, 0.8, 
                                   facecolor=WeeklyReportGenerator.COLORS['background'], 
                                   edgecolor='#4a5568', linewidth=0.5)
                ax.add_patch(rect)
                
                # Draw text
                text_color = '#000000' if bgcolor else WeeklyReportGenerator.COLORS['text_white']
                ax.text(x_pos + (0 if align == 'left' else width/2), y, value,
                       ha=align, va='center', fontsize=6, color=text_color)
                x_pos += width
    
    @staticmethod
    def _draw_daily_table(ax, day_data, benchmarks):
        """Draw daily breakdown table with borders"""
        import numpy as np
        ax.axis('off')
        from matplotlib.patches import Rectangle

        HEADER_BG = WeeklyReportGenerator.COLORS['header_bg']
        ROW_BG    = WeeklyReportGenerator.COLORS['background']
        WHITE     = WeeklyReportGenerator.COLORS['text_white']
        BORDER    = '#4a5568'
        DARK_BG   = '#2d3748'

        # 18 colonnes : 0=JOUR 1=MIN 2=DIST 3=%DIST 4=HSR 5=%HSR
        #               6=SPRINT 7=%SPRINT 8=VMAX 9=%VMAX
        #               10=DEC 11=%DEC 12=PP 13=%PP
        #               14=VOL 15=INT 16=VOLUME 17=INTENSITE
        headers = ['JOUR', 'MIN', 'DIST', '%DIST', 'HSR', '%HSR',
                   'SPRINT', '%SPRINT', 'VMAX', '%VMAX',
                   'DEC', '%DEC', 'PP', '%PP',
                   'VOL', 'INT', 'VOLUME', 'INTENSITE']

        _raw_w = [2.0, 0.7, 0.85, 0.7, 0.8, 0.7, 0.8, 0.7, 0.75, 0.7,
                  0.75, 0.7, 0.75, 0.7, 0.7, 0.7, 0.8, 0.8]
        _scale     = 15.0 / sum(_raw_w)
        col_widths = [w * _scale for w in _raw_w]

        def cx(i):
            return sum(col_widths[:i])

        def draw_cell(i, y, span=1, h=0.45, bg=ROW_BG, border=BORDER):
            x = cx(i)
            w = sum(col_widths[i:i + span])
            ax.add_patch(Rectangle((x, y - h/2), w, h,
                                   facecolor=bg, edgecolor=border, linewidth=0.5))

        def cell_text(i, y, text, span=1, fontsize=6.5, bold=False, color=WHITE):
            x = cx(i)
            w = sum(col_widths[i:i + span])
            ax.text(x + w/2, y, str(text), ha='center', va='center',
                    fontsize=fontsize,
                    fontweight='bold' if bold else 'normal',
                    color=color)

        ax.set_xlim(-0.1, sum(col_widths) + 0.1)
        ax.set_ylim(0, 11)

        # ── Header ───────────────────────────────────────────────────────
        for i, h in enumerate(headers):
            draw_cell(i, 10.25, bg=HEADER_BG, border='white')
            cell_text(i, 10.25, h, bold=True)

        # ── Data rows ────────────────────────────────────────────────────
        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        ordered_keys = []
        for base in DAY_BASE:
            if base in day_data:
                ordered_keys.append(base)
            if f'{base} MA' in day_data:
                ordered_keys.append(f'{base} MA')
            if f'{base} AP' in day_data:
                ordered_keys.append(f'{base} AP')

        # Max VMAX de la semaine (pour %VMAX relatif)
        max_vmax_kh_week = max(
            (d.get('top_speed', 0) * 3.6 for d in day_data.values()), default=0
        )

        row_y = 9.7

        all_minutes, all_dist_km, all_hsr_m, all_sprint_m = [], [], [], []
        all_vmax_kh, all_dec, all_pp = [], [], []
        all_vol_pct, all_int_pct, all_volume, all_intensite = [], [], [], []
        all_dist_pct, all_hsr_pct, all_sprint_pct, all_dec_pct, all_pp_pct = [], [], [], [], []

        for day in ordered_keys:
            data = day_data[day]
            parts = day.split(' ', 1)
            label    = parts[0][:3] + (f' {parts[1]}' if len(parts) > 1 else '')
            pc       = data['player_count'] if data['player_count'] > 0 else 1
            minutes  = data['duration'] // pc // 60        # moyenne par joueur → durée réelle de séance
            distance = round(data['distance_km'] / pc, 2)  # moyenne par joueur (km)
            hsr_m    = int((data.get('speed_zone_3_km', 0)
                            + data.get('speed_zone_4_km', 0)
                            + data.get('speed_zone_5_km', 0)) * 1000 / pc)  # moyenne par joueur (m)
            sprint_m = int(data.get('sprint_distance_m', 0) / pc)   # moyenne par joueur (m)
            vmax_kh  = round(data.get('top_speed', 0) * 3.6, 1)     # max séance (km/h)
            dec      = int(data.get('decel_high_count', 0) / pc)    # moyenne par joueur (DEC > 4 m/s/s)
            pp_val   = int(data['power_plays']             / pc)     # moyenne par joueur

            # Totaux bruts (équipe) pour le calcul des % — le benchmark est lui aussi un total équipe/séance
            raw_dist  = data['distance_km']
            raw_hsr   = (data.get('speed_zone_3_km', 0)
                         + data.get('speed_zone_4_km', 0)
                         + data.get('speed_zone_5_km', 0)) * 1000
            raw_spr   = data.get('sprint_distance_m', 0)
            raw_dec   = data.get('decel_high_count', 0)  # Deceleration Zone Count: > 4 m/s/s
            raw_pp    = data['power_plays']

            dist_pct   = int((raw_dist / benchmarks.get('distance_km',  1)) * 100) \
                         if benchmarks.get('distance_km',  0) > 0 else 0
            hsr_pct    = int((raw_hsr  / benchmarks.get('hsr_total',    1)) * 100) \
                         if benchmarks.get('hsr_total',    0) > 0 else 0
            sprint_pct = int((raw_spr  / benchmarks.get('sprint_total', 1)) * 100) \
                         if benchmarks.get('sprint_total', 0) > 0 else 0
            vmax_pct   = int((vmax_kh  / max_vmax_kh_week) * 100) \
                         if max_vmax_kh_week > 0 else 0
            dec_pct    = int((raw_dec  / benchmarks.get('dec_total',    1)) * 100) \
                         if benchmarks.get('dec_total',    0) > 0 else 0
            pp_pct     = int((raw_pp   / benchmarks.get('power_plays',  1)) * 100) \
                         if benchmarks.get('power_plays',  0) > 0 else 0

            vol_pct = int((dist_pct + hsr_pct + sprint_pct) / 3)
            int_pct = int((hsr_pct  + dec_pct  + pp_pct)    / 3)
            volume_val    = round((vol_pct / minutes) * 100, 1) if minutes else 0
            intensite_val = round((int_pct / minutes) * 100, 1) if minutes else 0

            all_minutes.append(minutes);   all_dist_km.append(distance)
            all_hsr_m.append(hsr_m);       all_sprint_m.append(sprint_m)
            all_vmax_kh.append(vmax_kh);   all_dec.append(dec)
            all_pp.append(pp_val);         all_vol_pct.append(vol_pct)
            all_int_pct.append(int_pct);   all_volume.append(volume_val)
            all_intensite.append(intensite_val)
            all_dist_pct.append(dist_pct); all_hsr_pct.append(hsr_pct)
            all_sprint_pct.append(sprint_pct)
            all_dec_pct.append(dec_pct);   all_pp_pct.append(pp_pct)

            # Cellules valeur
            draw_cell(0, row_y); cell_text(0, row_y, label)
            draw_cell(1, row_y); cell_text(1, row_y, str(minutes))
            draw_cell(2, row_y); cell_text(2, row_y, f'{distance:.2f}')
            bg = SessionReportGenerator.get_color_for_pct(dist_pct)
            draw_cell(3, row_y, bg=bg); cell_text(3, row_y, f'{dist_pct}%', color='#000000')
            draw_cell(4, row_y); cell_text(4, row_y, str(hsr_m))
            bg = SessionReportGenerator.get_color_for_pct(hsr_pct)
            draw_cell(5, row_y, bg=bg); cell_text(5, row_y, f'{hsr_pct}%', color='#000000')
            draw_cell(6, row_y); cell_text(6, row_y, str(sprint_m))
            bg = SessionReportGenerator.get_color_for_pct(sprint_pct)
            draw_cell(7, row_y, bg=bg); cell_text(7, row_y, f'{sprint_pct}%', color='#000000')
            draw_cell(8, row_y); cell_text(8, row_y, f'{vmax_kh:.1f}')
            bg = SessionReportGenerator.get_color_for_pct(vmax_pct)
            draw_cell(9, row_y, bg=bg); cell_text(9, row_y, f'{vmax_pct}%', color='#000000')
            draw_cell(10, row_y); cell_text(10, row_y, str(dec))
            bg = SessionReportGenerator.get_color_for_pct(dec_pct)
            draw_cell(11, row_y, bg=bg); cell_text(11, row_y, f'{dec_pct}%', color='#000000')
            draw_cell(12, row_y); cell_text(12, row_y, str(pp_val))
            bg = SessionReportGenerator.get_color_for_pct(pp_pct)
            draw_cell(13, row_y, bg=bg); cell_text(13, row_y, f'{pp_pct}%', color='#000000')
            bg = SessionReportGenerator.get_color_for_pct(vol_pct)
            draw_cell(14, row_y, bg=bg); cell_text(14, row_y, f'{vol_pct}%', color='#000000')
            bg = SessionReportGenerator.get_color_for_pct(int_pct)
            draw_cell(15, row_y, bg=bg); cell_text(15, row_y, f'{int_pct}%', color='#000000')
            draw_cell(16, row_y); cell_text(16, row_y, f'{volume_val}%')
            draw_cell(17, row_y); cell_text(17, row_y, f'{intensite_val}%')

            row_y -= 0.5

        # ── MONOTONIE ────────────────────────────────────────────────────
        row_y -= 0.1

        def _mono(vals):
            a = np.array(vals, dtype=float)
            return f'{np.mean(a) / np.std(a):.2f}' if len(a) > 1 and np.std(a) > 0 else ''

        draw_cell(0, row_y, bg=DARK_BG); cell_text(0, row_y, 'MONOTONIE', bold=True)
        draw_cell(1, row_y, bg=DARK_BG); cell_text(1, row_y, str(len(ordered_keys)), bold=True)
        for col_i, vals in [(2, all_dist_km), (4, all_hsr_m),  (6, all_sprint_m),
                            (8, all_vmax_kh), (10, all_dec),   (12, all_pp)]:
            draw_cell(col_i, row_y, span=2, bg=DARK_BG)
            cell_text(col_i, row_y, _mono(vals), span=2, bold=True)
        draw_cell(14, row_y, bg=DARK_BG)
        draw_cell(15, row_y, bg=DARK_BG)
        draw_cell(16, row_y, bg=DARK_BG)
        draw_cell(17, row_y, bg=DARK_BG)
        row_y -= 0.5

        # ── TOTAL ────────────────────────────────────────────────────────
        tot_min    = sum(all_minutes)
        tot_dist   = round(sum(all_dist_km), 2)
        tot_hsr    = sum(all_hsr_m)
        tot_sprint = sum(all_sprint_m)
        tot_dec    = sum(all_dec)
        tot_pp     = sum(all_pp)
        # % totaux = somme des % journaliers
        tot_dist_pct   = sum(all_dist_pct)
        tot_hsr_pct    = sum(all_hsr_pct)
        tot_sprint_pct = sum(all_sprint_pct)
        tot_dec_pct    = sum(all_dec_pct)
        tot_pp_pct     = sum(all_pp_pct)
        # VMAX = moyenne des valeurs journalières, %VMAX vs objectif 31.51
        avg_vmax       = round(sum(all_vmax_kh) / len(all_vmax_kh), 2) if all_vmax_kh else 0
        tot_vmax_pct   = int(avg_vmax / 31.51 * 100) if avg_vmax > 0 else 0

        total_vals = [
            'TOTAL',                       str(tot_min),
            f'{tot_dist:.2f}',             f'{tot_dist_pct}%',
            str(tot_hsr),                  f'{tot_hsr_pct}%',
            str(tot_sprint),               f'{tot_sprint_pct}%',
            f'{avg_vmax:.2f}',             f'{tot_vmax_pct}%',
            str(tot_dec),                  f'{tot_dec_pct}%',
            str(tot_pp),                   f'{tot_pp_pct}%',
            '',                            '',
            '',                            '',
        ]
        for i, val in enumerate(total_vals):
            draw_cell(i, row_y, bg=DARK_BG)
            cell_text(i, row_y, val, bold=True)
        row_y -= 0.5

        # ── OBJECTIF ─────────────────────────────────────────────────────
        obj_vals = ['OBJECTIF', '', '28.38', '250%', '2700', '150%',
                    '909', '85%', '31.51', '95%', '120', '250%', '185', '200%',
                    '', '', '', '']
        for i, val in enumerate(obj_vals):
            draw_cell(i, row_y, bg=DARK_BG)
            cell_text(i, row_y, val, bold=True)
    
    @staticmethod
    def _draw_trend_graph(ax, day_data, benchmarks):
        """Draw volume/intensity trend graph with percentages"""
        ax.set_facecolor(WeeklyReportGenerator.COLORS['background'])

        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        # Même logique que _draw_daily_table : clés ordonnées avec MA/AP
        ordered_keys = []
        for base in DAY_BASE:
            if base in day_data:
                ordered_keys.append(base)
            if f'{base} MA' in day_data:
                ordered_keys.append(f'{base} MA')
            if f'{base} AP' in day_data:
                ordered_keys.append(f'{base} AP')

        labels = []
        volumes = []
        intensities = []

        for day in ordered_keys:
            parts = day.split(' ', 1)
            label = parts[0][:3] + (f'\n{parts[1]}' if len(parts) > 1 else '')
            labels.append(label)
            data = day_data[day]
            vol_pct = int((data['distance_km'] / benchmarks.get('distance_km', 100)) * 100) if benchmarks.get('distance_km', 0) > 0 else 0
            hsr_pct = (data['sprint_distance_m'] / benchmarks.get('hsr_total', 5000)) * 100 if benchmarks.get('hsr_total', 0) > 0 else 0
            dec_pct = (data.get('decel_high_count', 0) / benchmarks.get('dec_total', 100)) * 100 if benchmarks.get('dec_total', 0) > 0 else 0
            pp_pct = (data['power_plays'] / benchmarks.get('power_plays', 200)) * 100 if benchmarks.get('power_plays', 0) > 0 else 0
            intensity_pct = int((hsr_pct + dec_pct + pp_pct) / 3)
            volumes.append(vol_pct)
            intensities.append(intensity_pct)

        x = range(len(labels))
        ax.plot(x, volumes, marker='o', color=WeeklyReportGenerator.COLORS['green'],
               linewidth=2, label='VOLUME')
        ax.plot(x, intensities, marker='s', color=WeeklyReportGenerator.COLORS['orange'],
               linewidth=2, label='INTENSITÉ')

        ax.set_xticks(x)
        ax.set_xticklabels(labels, color=WeeklyReportGenerator.COLORS['text_white'], fontsize=7)
        ax.tick_params(colors=WeeklyReportGenerator.COLORS['text_white'])
        ax.legend(facecolor=WeeklyReportGenerator.COLORS['gauge_bg'],
                 edgecolor=WeeklyReportGenerator.COLORS['text_gray'],
                 labelcolor=WeeklyReportGenerator.COLORS['text_white'])
        ax.grid(True, alpha=0.2, color=WeeklyReportGenerator.COLORS['text_gray'])
        ax.set_title('Évolution hebdomadaire', color=WeeklyReportGenerator.COLORS['text_white'],
                    fontweight='bold')
# Code à ajouter à la fin de report_generator.py

class IndividualWeekReportGenerator:
    """Generate individual player weekly microcycle reports"""
    
    COLORS = SessionReportGenerator.COLORS
    
    @staticmethod
    def calculate_player_max(all_sessions):
        """Calculate personal max for each metric across all player sessions"""
        if not all_sessions:
            return {}
        
        max_distance = max((s.get('distance_km', 0) * 1000 for s in all_sessions), default=0)
        max_hsr = max(((s.get('speed_zone_3_km', 0) + s.get('speed_zone_4_km', 0) + s.get('speed_zone_5_km', 0)) * 1000 for s in all_sessions), default=0)
        max_sprint = max((s.get('sprint_distance_m', 0) for s in all_sessions), default=0)
        max_vmax = max((s.get('top_speed', 0) for s in all_sessions), default=0) * 3.6  # m/s → km/h
        max_dec = max((s.get('decel_high_count', 0) for s in all_sessions), default=0)
        max_pp = max((s.get('power_plays', 0) for s in all_sessions), default=0)
        
        return {
            'distance': max_distance,
            'hsr': max_hsr,
            'sprint': max_sprint,
            'vmax': max_vmax,
            'dec': max_dec,
            'pp': max_pp
        }
    
    @staticmethod
    def aggregate_by_day_individual(session_data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate player data by day of week.
        Si un jour a deux séances (MA/AP), crée des clés séparées : 'MARDI MA', 'MARDI AP'.
        """
        from collections import defaultdict
        from datetime import datetime

        DAY_NAMES = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']

        def get_slot(title: str) -> str:
            t = str(title).upper()
            if 'MATIN' in t:
                return 'MA'
            if any(kw in t for kw in ['AM', 'APRES MIDI', 'APRÈS MIDI', 'APRES-MIDI', 'APRÈS-MIDI', 'APREM', 'PM']):
                return 'AP'
            if t.rstrip().endswith((' AP', '/AP', '-AP')):
                return 'AP'
            return ''

        def _empty():
            return {'duration': 0, 'distance': 0.0, 'hsr': 0.0, 'sprint': 0.0,
                    'vmax': 0.0, 'dec': 0, 'pp': 0, 'player_load': 0.0, 'session_count': 0}

        day_sessions = defaultdict(list)
        for session in session_data:
            date_str = session.get('date', '')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception:
                continue
            day_name = DAY_NAMES[date.weekday()]
            day_sessions[day_name].append(session)

        def _sum(sessions):
            totals = _empty()
            for s in sessions:
                hsr = (s.get('speed_zone_3_km', 0) + s.get('speed_zone_4_km', 0) + s.get('speed_zone_5_km', 0)) * 1000
                totals['duration']     += s.get('duration', 0)
                totals['distance']     += s.get('distance_km', 0) * 1000
                totals['hsr']          += hsr
                totals['sprint']       += s.get('sprint_distance_m', 0)
                totals['vmax']          = max(totals['vmax'], s.get('top_speed', 0))
                totals['dec']          += s.get('decel_high_count', 0)
                totals['pp']           += s.get('power_plays', 0)
                totals['player_load']  += s.get('player_load', 0)
                totals['session_count'] += 1
            return totals

        result = {}
        for day_name, sessions in day_sessions.items():
            slots = {get_slot(s.get('session_title', '')) for s in sessions}
            has_ma = 'MA' in slots
            has_ap = 'AP' in slots
            if has_ma or has_ap:
                ma_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'MA']
                ap_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'AP']
                other = [s for s in sessions if get_slot(s.get('session_title', '')) == '']
                # Garder les séances sans tag comme entrée de base séparée
                if other:
                    result[day_name] = _sum(other)
                if ma_sessions:
                    result[f'{day_name} MA'] = _sum(ma_sessions)
                if ap_sessions:
                    result[f'{day_name} AP'] = _sum(ap_sessions)
            else:
                result[day_name] = _sum(sessions)

        return result

    @staticmethod
    def aggregate_by_day_average(session_data: List[Dict]) -> Dict[str, Dict]:
        """Calculate average data by day of week across all players, with MA/AP slot support"""
        from collections import defaultdict
        from datetime import datetime

        def get_slot(title: str) -> str:
            t = str(title).upper()
            if 'MATIN' in t:
                return 'MA'
            if any(kw in t for kw in ['AM', 'APRES MIDI', 'APRÈS MIDI', 'APRES-MIDI', 'APRÈS-MIDI', 'APREM', 'PM']):
                return 'AP'
            if t.rstrip().endswith((' AP', '/AP', '-AP')):
                return 'AP'
            return ''

        # Group sessions by (day + slot) and player
        day_player_data = defaultdict(lambda: defaultdict(lambda: {
            'distance': 0,
            'hsr': 0,
            'sprint': 0,
            'vmax': 0,
            'dec': 0,
            'pp': 0,
            'player_load': 0,
            'session_count': 0
        }))
        
        # Accumulate data per player per day+slot
        for session in session_data:
            date_str = session['date']
            date = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE'][date.weekday()]
            slot = get_slot(session.get('session_title', '') or '')
            key = f'{day_name} {slot}' if slot else day_name
            player_name = session.get('player_name', 'Unknown')
            
            hsr = (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            
            day_player_data[key][player_name]['distance'] += session.get('distance_km', 0) * 1000
            day_player_data[key][player_name]['hsr'] += hsr
            day_player_data[key][player_name]['sprint'] += session.get('sprint_distance_m', 0)
            day_player_data[key][player_name]['vmax'] = max(day_player_data[key][player_name]['vmax'], session.get('top_speed', 0))
            day_player_data[key][player_name]['dec'] += session.get('decel_high_count', 0)
            day_player_data[key][player_name]['pp'] += session.get('power_plays', 0)
            day_player_data[key][player_name]['player_load'] += session.get('player_load', 0)
            day_player_data[key][player_name]['session_count'] += 1
        
        # Calculate averages across players for each day
        day_averages = {}
        for day_name, players in day_player_data.items():
            player_count = len(players)
            if player_count == 0:
                continue
            
            day_averages[day_name] = {
                'distance': sum(p['distance'] for p in players.values()) / player_count,
                'hsr': sum(p['hsr'] for p in players.values()) / player_count,
                'sprint': sum(p['sprint'] for p in players.values()) / player_count,
                'vmax': sum(p['vmax'] for p in players.values()) / player_count,
                'dec': sum(p['dec'] for p in players.values()) / player_count,
                'pp': sum(p['pp'] for p in players.values()) / player_count,
                'player_load': sum(p['player_load'] for p in players.values()) / player_count,
                'session_count': player_count
            }
        
        return day_averages
    
    @staticmethod
    def calculate_totals(session_data: List[Dict]) -> Dict:
        """Calculate week totals for a player or group"""
        total_distance = sum(s.get('distance_km', 0) * 1000 for s in session_data)
        total_hsr = sum((s.get('speed_zone_3_km', 0) + s.get('speed_zone_4_km', 0) + s.get('speed_zone_5_km', 0)) * 1000 for s in session_data)
        total_sprint = sum(s.get('sprint_distance_m', 0) for s in session_data)
        max_vmax = max((s.get('top_speed', 0) for s in session_data), default=0)
        total_dec = sum(s.get('decel_high_count', 0) for s in session_data)
        total_pp = sum(s.get('power_plays', 0) for s in session_data)
        total_player_load = sum(s.get('player_load', 0) for s in session_data)
        
        return {
            'distance': total_distance,
            'hsr': total_hsr,
            'sprint': total_sprint,
            'vmax': max_vmax,
            'dec': total_dec,
            'pp': total_pp,
            'player_load': total_player_load
        }
    
    @staticmethod
    def calculate_average(session_data: List[Dict]) -> Dict:
        """Calculate average per session for a group"""
        if not session_data:
            return {'distance': 0, 'hsr': 0, 'sprint': 0, 'vmax': 0, 'dec': 0, 'pp': 0, 'player_load': 0}
        
        totals = IndividualWeekReportGenerator.calculate_totals(session_data)
        count = len(session_data)
        
        return {
            'distance': totals['distance'] / count,
            'hsr': totals['hsr'] / count,
            'sprint': totals['sprint'] / count,
            'vmax': totals['vmax'],  # Max, not average
            'dec': totals['dec'] / count,
            'pp': totals['pp'] / count,
            'player_load': totals['player_load'] / count
        }
    
    @staticmethod
    def _draw_header(ax, player_name, position, week_start, week_end, week_number, tags=""):
        """Draw header section - same style as weekly report"""
        from matplotlib import patches
        from PIL import Image
        from matplotlib.offsetbox import OffsetImage, AnnotationBbox
        
        ax.set_facecolor('none')
        
        # White rectangle (same dimensions as weekly report)
        rect = patches.Rectangle((0.01, 0.25), 0.97, 0.5, linewidth=1, 
                                edgecolor='none', facecolor='#ffffff', zorder=0)
        ax.add_patch(rect)
        
        # Logo (same size as weekly report)
        try:
            logo = Image.open('assets/logo.png')
            imagebox = OffsetImage(logo, zoom=0.21)
            ab = AnnotationBbox(imagebox, (0.13, 0.5), frameon=False, 
                              xycoords='axes fraction', box_alignment=(0.5, 0.5))
            ax.add_artist(ab)
        except:
            pass
        
        # Title
        ax.text(0.44, 0.55, 'Rapport Hebdomadaire Individuel',
                ha='center', va='center',
                fontsize=28, fontweight='bold',
                color='#1a2332', zorder=10)
        ax.text(0.44, 0.4, player_name,
                ha='center', va='center',
                fontsize=14, fontweight='bold',
                color='#1a2332', zorder=10)
        
        # Info boxes
        info_y = 0.5
        ax.text(0.70, info_y + 0.15, 'POSTE', ha='center', va='center', fontsize=9, color='#718096', zorder=10)
        ax.text(0.70, info_y - 0.15, position, ha='center', va='center', fontsize=11, fontweight='bold', color='#1a2332', zorder=10)
        
        ax.text(0.80, info_y + 0.15, 'DATE', ha='center', va='center', fontsize=9, color='#718096', zorder=10)
        ax.text(0.80, info_y - 0.10, f'Du {week_start}', ha='center', va='center', fontsize=11, fontweight='bold', color='#1a2332', zorder=10)
        ax.text(0.80, info_y - 0.15, f'au {week_end}', ha='center', va='center', fontsize=11, fontweight='bold', color='#1a2332', zorder=10)
        
        ax.text(0.90, info_y + 0.15, 'NUMÉRO DE SEMAINE', ha='center', va='center', fontsize=9, color='#718096', zorder=10)
        ax.text(0.90, info_y - 0.15, str(week_number), ha='center', va='center', fontsize=11, fontweight='bold', color='#1a2332', zorder=10)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    
    @staticmethod
    def _draw_daily_table(ax, daily_data, player_max, player_name):
        """Draw main day-by-day table with percentages"""
        ax.axis('off')
        ax.set_xlim(0, 16)
        n_rows = len(daily_data)
        # header(1) + data rows + TOTAL(1.1) + OBJECTIF(1) + MONOTONIE(1) + margin
        min_height = 1 + n_rows + 3.5
        ylim_max = max(12, min_height + 1)
        ax.set_ylim(0, ylim_max)

        from matplotlib.patches import Rectangle
        import numpy as np

        # Headers
        headers = ['JOUR', 'MINUTES', 'DISTANCE', '%DIST', 'HSR', '%HSR', 'SPRINT', '%SPRINT', 'VMAX', '%VMAX', 'DEC', '%DEC', 'POWER PLAY', '%PP', 'PLAYER LOAD']
        col_widths = [1.5, 0.8, 0.9, 0.7, 0.8, 0.7, 0.8, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0, 0.7, 1.2]

        x_pos = 0
        y_top = ylim_max - 2  # toujours ancré 1 unité sous le bord supérieur
        y = y_top
        for header, width in zip(headers, col_widths):
            rect = Rectangle((x_pos, y-0.4), width, 0.8,
                           facecolor=IndividualWeekReportGenerator.COLORS['header_bg'], 
                           edgecolor='white', linewidth= 0.5)
            ax.add_patch(rect)
            
            ax.text(x_pos + width/2, y, header, ha='center', va='center',
                   fontsize=7, fontweight='bold', color=IndividualWeekReportGenerator.COLORS['text_white'])
            x_pos += width
        
        # Days
        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        def _ordered_keys(d):
            keys = []
            for base in DAY_BASE:
                if base in d:
                    keys.append(base)
                if f'{base} MA' in d:
                    keys.append(f'{base} MA')
                if f'{base} AP' in d:
                    keys.append(f'{base} AP')
            return keys
        def _day_label(key):
            parts = key.split(' ', 1)
            return parts[0][:3] + (f' {parts[1]}' if len(parts) > 1 else '')

        days_order = _ordered_keys(daily_data)

        # Aggregate player loads for monotonie calculation
        player_loads = [daily_data[day].get('player_load', 0) for day in days_order if daily_data[day].get('session_count', 0) > 0]

        # Calculate totals
        total_minutes = sum(daily_data[day].get('duration', 0) for day in days_order) // 60
        total_distance = sum(daily_data[day].get('distance', 0) for day in days_order)
        total_hsr = sum(daily_data[day].get('hsr', 0) for day in days_order)
        total_sprint = sum(daily_data[day].get('sprint', 0) for day in days_order)
        max_vmax = max((daily_data[day].get('vmax', 0) for day in days_order), default=0) * 3.6  # m/s → km/h
        total_dec = sum(daily_data[day].get('dec', 0) for day in days_order)
        total_pp = sum(daily_data[day].get('pp', 0) for day in days_order)
        total_player_load = sum(player_loads)
        
        # Calculate monotonie
        if len(player_loads) > 1 and np.std(player_loads) > 0:
            monotonie = np.mean(player_loads) / np.std(player_loads)
        else:
            monotonie = 0
        
        # Day rows
        for day in days_order:
            y -= 1
            day_info = daily_data.get(day, {})

            if day_info.get('session_count', 0) == 0:
                row_data = [(_day_label(day), None, 'center')] + [('', None, 'center')] * 14
            else:
                minutes = day_info['duration'] // 60
                distance_m = day_info['distance']  # mètres pour calcul %
                distance = distance_m / 1000  # km pour affichage
                hsr = int(day_info['hsr'])
                sprint = int(day_info['sprint'])
                vmax = day_info['vmax'] * 3.6  # m/s → km/h
                dec = day_info['dec']
                pp = day_info['pp']
                pl = day_info['player_load']
                
                # Calculate percentages
                dist_pct = int((distance_m / player_max['distance'] * 100)) if player_max['distance'] > 0 else 0
                hsr_pct = int((hsr / player_max['hsr'] * 100)) if player_max['hsr'] > 0 else 0
                sprint_pct = int((sprint / player_max['sprint'] * 100)) if player_max['sprint'] > 0 else 0
                vmax_pct = int((vmax / player_max['vmax'] * 100)) if player_max['vmax'] > 0 else 0
                dec_pct = int((dec / player_max['dec'] * 100)) if player_max['dec'] > 0 else 0
                pp_pct = int((pp / player_max['pp'] * 100)) if player_max['pp'] > 0 else 0
                
                row_data = [
                    (_day_label(day), None, 'center'),
                    (str(minutes), None, 'center'),
                    (f'{distance:.2f}', None, 'center'),
                    (f'{dist_pct}%', SessionReportGenerator.get_color_for_pct(dist_pct), 'center'),
                    (str(hsr), None, 'center'),
                    (f'{hsr_pct}%', SessionReportGenerator.get_color_for_pct(hsr_pct), 'center'),
                    (str(sprint), None, 'center'),
                    (f'{sprint_pct}%', SessionReportGenerator.get_color_for_pct(sprint_pct), 'center'),
                    (f'{vmax:.1f}', None, 'center'),
                    (f'{vmax_pct}%', SessionReportGenerator.get_color_for_pct(vmax_pct), 'center'),
                    (str(dec), None, 'center'),
                    (f'{dec_pct}%', SessionReportGenerator.get_color_for_pct(dec_pct), 'center'),
                    (str(pp), None, 'center'),
                    (f'{pp_pct}%', SessionReportGenerator.get_color_for_pct(pp_pct), 'center'),
                    (f'{pl:.1f}', None, 'center')
                ]
            
            x_pos = 0
            for (value, bgcolor, align), width in zip(row_data, col_widths):
                if bgcolor:
                    rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                                   facecolor=bgcolor, edgecolor='#4a5568', linewidth=0.5)
                else:
                    rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                                   facecolor=IndividualWeekReportGenerator.COLORS['background'], 
                                   edgecolor='#4a5568', linewidth=0.5)
                ax.add_patch(rect)
                
                text_color = '#000000' if bgcolor else IndividualWeekReportGenerator.COLORS['text_white']
                ax.text(x_pos + width/2, y, value,
                       ha='center', va='center', fontsize=7, color=text_color)
                x_pos += width
        
        # TOTAL row
        y -= 1.1
        total_row_data = [
            ('TOTAL', None, 'center'),
            (str(total_minutes), None, 'center'),
            (f'{total_distance/1000:.2f}', None, 'center'),
            (f'{int((total_distance / player_max["distance"] * 100)) if player_max["distance"] > 0 else 0}%', None, 'center'),
            (str(int(total_hsr)), None, 'center'),
            (f'{int((total_hsr / player_max["hsr"] * 100)) if player_max["hsr"] > 0 else 0}%', None, 'center'),
            (str(int(total_sprint)), None, 'center'),
            (f'{int((total_sprint / player_max["sprint"] * 100)) if player_max["sprint"] > 0 else 0}%', None, 'center'),
            (f'{max_vmax:.1f}', None, 'center'),
            (f'{int((max_vmax / player_max["vmax"] * 100)) if player_max["vmax"] > 0 else 0}%', None, 'center'),
            (str(total_dec), None, 'center'),
            (f'{int((total_dec / player_max["dec"] * 100)) if player_max["dec"] > 0 else 0}%', None, 'center'),
            (str(total_pp), None, 'center'),
            (f'{int((total_pp / player_max["pp"] * 100)) if player_max["pp"] > 0 else 0}%', None, 'center'),
            (f'{total_player_load:.1f}', None, 'center')
        ]
        
        x_pos = 0
        for (value, _, align), width in zip(total_row_data, col_widths):
            rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                           facecolor='#2d3748', edgecolor='#4a5568', linewidth=0.5)
            ax.add_patch(rect)
            
            ax.text(x_pos + width/2, y, value,
                   ha='center', va='center', fontsize=7, fontweight='bold', 
                   color=IndividualWeekReportGenerator.COLORS['text_white'])
            x_pos += width
        
        # OBJECTIF row
        y -= 1
        objectif_row_data = [
            ('OBJECTIF', None, 'center'),
            ('', None, 'center'),
            ('', None, 'center'),
            ('200%', None, 'center'),
            ('', None, 'center'),
            ('100%', None, 'center'),
            ('', None, 'center'),
            ('100%', None, 'center'),
            ('', None, 'center'),
            ('100%', None, 'center'),
            ('', None, 'center'),
            ('100%', None, 'center'),
            ('', None, 'center'),
            ('100%', None, 'center'),
            ('', None, 'center')
        ]
        
        x_pos = 0
        for (value, _, align), width in zip(objectif_row_data, col_widths):
            rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                           facecolor=IndividualWeekReportGenerator.COLORS['background'], 
                           edgecolor='#4a5568', linewidth=0.5)
            ax.add_patch(rect)
            
            ax.text(x_pos + width/2, y, value,
                   ha='center', va='center', fontsize=7, 
                   color=IndividualWeekReportGenerator.COLORS['text_white'])
            x_pos += width
        
        # MONOTONIE row
        y -= 1
        mono_row_data = [
            ('MONOTONIE', None, 'center'),
            (f'{monotonie:.2f}' if monotonie > 0 else '', SessionReportGenerator.COLORS['pink'], 'center')
        ] + [('', None, 'center')] * 13
        
        x_pos = 0
        for i, ((value, bgcolor, align), width) in enumerate(zip(mono_row_data, col_widths)):
            if i == 1 and bgcolor:
                rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                               facecolor=bgcolor, edgecolor='#4a5568', linewidth=0.5)
            else:
                rect = Rectangle((x_pos, y-0.5), width, 1.0, 
                               facecolor=IndividualWeekReportGenerator.COLORS['background'], 
                               edgecolor='#4a5568', linewidth=0.5)
            ax.add_patch(rect)
            
            ax.text(x_pos + width/2, y, value,
                   ha='center', va='center', fontsize=7, 
                   color=IndividualWeekReportGenerator.COLORS['text_white'])
            x_pos += width

    
    @staticmethod
    def _draw_graphs(ax, player_daily, position_daily, team_daily):
        """Draw 6 mini bar charts with 3 bars per day (player, position avg, team avg)"""
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        
        # Construire la liste ordonnée des jours en tenant compte des séances MA/AP
        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        all_keys = set(list(player_daily.keys()) + list(position_daily.keys()) + list(team_daily.keys()))
        days_order = []
        for base in DAY_BASE:
            if base in all_keys:
                days_order.append(base)
            if f'{base} MA' in all_keys:
                days_order.append(f'{base} MA')
            if f'{base} AP' in all_keys:
                days_order.append(f'{base} AP')
        day_labels = [p[:3] + (' ' + p.split(' ', 1)[1] if ' ' in p else '') for p in days_order]

        # Extract data for each metric from all 3 sources
        import numpy as np

        def get_metric_data(daily_data, metric_key, divisor=1):
            return [daily_data.get(day, {}).get(metric_key, 0) / divisor for day in days_order]
        
        metrics_config = [
            ('DISTANCE', 'distance', 1000),
            ('HSR', 'hsr', 1),
            ('SPRINT', 'sprint', 1),
            ('VMAX', 'vmax', 1),
            ('DEC', 'dec', 1),
            ('POWER PLAY', 'pp', 1)
        ]
        
        # Colors matching the legend (player=orange, position=red, team=white)
        colors = ['#FFA500', '#FF0000', '#FFFFFF']
        
        # Position for 6 graphs (2 rows x 3 cols)
        positions = [
            (0.0, 0.65, 0.3, 0.47),   # DISTANCE (top row)
            (0.33, 0.65, 0.3, 0.47),  # HSR
            (0.66, 0.65, 0.3, 0.47),  # SPRINT
            (0.0, 0.0, 0.3, 0.47),    # VMAX (bottom row)
            (0.33, 0.0, 0.3, 0.47),   # DEC
            (0.66, 0.0, 0.3, 0.47)    # POWER PLAY
        ]
        
        for idx, (metric_name, metric_key, divisor) in enumerate(metrics_config):
            x, y, w, h = positions[idx]
            graph_ax = ax.inset_axes([x, y, w, h])
            
            # Get data from all 3 sources
            player_values = get_metric_data(player_daily, metric_key, divisor)
            position_values = get_metric_data(position_daily, metric_key, divisor)
            team_values = get_metric_data(team_daily, metric_key, divisor)
            
            # Bar width and positions for grouped bars
            bar_width = 0.25
            x_pos = np.arange(len(days_order))
            
            # Draw 3 bars per day
            graph_ax.bar(x_pos - bar_width, player_values, bar_width, color=colors[0], label='JOUEUR')
            graph_ax.bar(x_pos, position_values, bar_width, color=colors[1], label='MAX POSTE')
            graph_ax.bar(x_pos + bar_width, team_values, bar_width, color=colors[2], label='MOYENNE EQUIPE')
            
            # Add value labels on top of each bar
            for i, (pv, posv, tv) in enumerate(zip(player_values, position_values, team_values)):
                if pv > 0:
                    graph_ax.text(i - bar_width, pv, f'{int(pv)}', ha='center', va='bottom', fontsize=5, color='white')
                if posv > 0:
                    graph_ax.text(i, posv, f'{int(posv)}', ha='center', va='bottom', fontsize=5, color='white')
                if tv > 0:
                    graph_ax.text(i + bar_width, tv, f'{int(tv)}', ha='center', va='bottom', fontsize=5, color='white')
            
            # Styling
            graph_ax.set_title(metric_name, fontsize=12, fontweight='bold', color='white', pad=5)
            graph_ax.set_xticks(x_pos)
            graph_ax.set_xticklabels(day_labels, fontsize=6, rotation=45, ha='right', color='white')
            graph_ax.tick_params(axis='y', labelsize=6, colors='white')
            graph_ax.set_facecolor('#1a202c')
            for spine in graph_ax.spines.values():
                spine.set_edgecolor('#4a5568')
            graph_ax.grid(axis='y', alpha=0.2, color='white')

    @staticmethod
    def _draw_comparison_tables(ax, player_daily, position_daily, team_daily):
        """Draw 3 comparison tables (player, position, team) with 7 day rows + TOTAL"""
        ax.axis('off')
        # xlim/ylim set dynamically below after position computation
        from matplotlib.patches import Rectangle

        # Layout parameters
        headers = ['JOUR', 'DIST', 'HSR', 'SPRINT', 'VMAX', 'DEC', 'PP', 'LOAD']
        jour_w = 0.11
        data_w = (1.0 - jour_w) / 7
        col_widths = [jour_w] + [data_w] * 7
        col_width = data_w  # compatibilité
        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        all_keys_comp = set(list(player_daily.keys()) + list(position_daily.keys()) + list(team_daily.keys()))
        days_order = []
        for base in DAY_BASE:
            if base in all_keys_comp:
                days_order.append(base)
            if f'{base} MA' in all_keys_comp:
                days_order.append(f'{base} MA')
            if f'{base} AP' in all_keys_comp:
                days_order.append(f'{base} AP')
        def _daylabel(k):
            parts = k.split(' ', 1)
            return parts[0][:3] + (f' {parts[1]}' if len(parts) > 1 else '')
        row_h = 0.032
        header_h = 0.04
        rect_h = 0.032
        gap = 0.025

        def table_height():
            return 0.115 + len(days_order) * row_h + rect_h / 2

        def draw_table(x0, y_top, title, data_daily, title_color):
            # Title
            # Draw title background
            title_rect = Rectangle((x0, y_top + 0.03), 1.0, 0.04,
                                  facecolor=title_color, edgecolor='white', linewidth=1)
            ax.add_patch(title_rect)
            # Title text (white for orange/red, black for white background)
            text_color = 'black' if title_color == '#FFFFFF' else 'white'
            ax.text(x0 + 0.5, y_top + 0.05, title, ha='center', va='center', 
                   fontsize=8, fontweight='bold', color=text_color)
            
            # Headers
            x_pos = x0
            for header, cw in zip(headers, col_widths):
                rect = Rectangle((x_pos, y_top - 0.01), cw, header_h,
                               facecolor=IndividualWeekReportGenerator.COLORS['header_bg'],
                               edgecolor='white', linewidth=0.5)
                ax.add_patch(rect)
                ax.text(x_pos + cw/2, y_top + 0.005, header, ha='center', va='center',
                       fontsize=7, fontweight='bold',
                       color=IndividualWeekReportGenerator.COLORS['text_white'])
                x_pos += cw

            # Day rows
            for i, day in enumerate(days_order):
                y = y_top - 0.03 - i * row_h
                vals = data_daily.get(day, {})
                distance_m = vals.get('distance', 0)
                distance = distance_m / 1000  # km pour affichage
                hsr = int(vals.get('hsr', 0))
                sprint = int(vals.get('sprint', 0))
                vmax = vals.get('vmax', 0) * 3.6  # m/s → km/h
                dec = int(vals.get('dec', 0))
                pp = int(vals.get('pp', 0))
                load = vals.get('player_load', 0)

                row_values = [_daylabel(day), f'{distance:.2f}', f'{hsr}', f'{sprint}', f'{vmax:.1f}',
                              f'{dec}', f'{pp}', f'{load:.1f}']
                x_pos = x0
                for value, cw in zip(row_values, col_widths):
                    rect = Rectangle((x_pos, y - rect_h/2), cw, rect_h,
                                   facecolor=IndividualWeekReportGenerator.COLORS['background'],
                                   edgecolor='#4a5568', linewidth=0.5)
                    ax.add_patch(rect)
                    ax.text(x_pos + cw/2, y, value, ha='center', va='center',
                           fontsize=7, color=IndividualWeekReportGenerator.COLORS['text_white'])
                    x_pos += cw

            # TOTAL row
            y_total = y_top - 0.035 - len(days_order) * row_h
            total_distance = sum(int(data_daily.get(d, {}).get('distance', 0)) for d in days_order)
            total_hsr = sum(int(data_daily.get(d, {}).get('hsr', 0)) for d in days_order)
            total_sprint = sum(int(data_daily.get(d, {}).get('sprint', 0)) for d in days_order)
            max_vmax = max((data_daily.get(d, {}).get('vmax', 0) for d in days_order), default=0) * 3.6  # m/s → km/h
            total_dec = sum(int(data_daily.get(d, {}).get('dec', 0)) for d in days_order)
            total_pp = sum(int(data_daily.get(d, {}).get('pp', 0)) for d in days_order)
            total_load = sum(float(data_daily.get(d, {}).get('player_load', 0)) for d in days_order)

            totals = ['TOTAL', f'{total_distance/1000:.2f}', f'{total_hsr}', f'{total_sprint}', f'{max_vmax:.1f}',
                      f'{total_dec}', f'{total_pp}', f'{total_load:.1f}']
            x_pos = x0
            for value, cw in zip(totals, col_widths):
                rect = Rectangle((x_pos, y_total - rect_h/2), cw, rect_h,
                               facecolor='#2d3748', edgecolor='#4a5568', linewidth=0.5)
                ax.add_patch(rect)
                ax.text(x_pos + cw/2, y_total, value, ha='center', va='center',
                       fontsize=7, fontweight='bold',
                       color=IndividualWeekReportGenerator.COLORS['text_white'])
                x_pos += cw

        # Compute table height and place tables non-overlapping
        th = table_height()
        top_y = 0.95
        mid_y = top_y - th - gap
        bot_y = mid_y - th - gap

        # Bas réel = bord inférieur de la ligne TOTAL du 3e tableau
        actual_bottom = bot_y - 0.045 - len(days_order) * row_h - rect_h / 2

        # Pas de scaling : on laisse le ylim dynamique couvrir tout le contenu
        ax.set_xlim(-0.005, 1.005)
        ax.set_ylim(actual_bottom - 0.03, top_y + 0.6)

        # Draw the three tables
        draw_table(0.0, top_y, 'PLAYER', player_daily, '#FFA500')
        draw_table(0.0, mid_y, 'MOYENNE POSTE', position_daily, '#FF0000')
        draw_table(0.0, bot_y, 'MOYENNE EQUIPE', team_daily, '#FFFFFF')

    @staticmethod
    def generate_individual_week_report(
        player_sessions: List[Dict[str, Any]],
        all_player_sessions: List[Dict[str, Any]],
        same_position_sessions: List[Dict[str, Any]],
        team_sessions: List[Dict[str, Any]],
        player_name: str,
        position: str,
        week_number: int,
        year: int,
        week_start: str,
        week_end: str
    ) -> str:
        """
        Generate individual player weekly report
        
        Returns:
            Base64 encoded PNG image
        """
        # Calculate player max
        player_max = IndividualWeekReportGenerator.calculate_player_max(all_player_sessions)
        
        # Aggregate data
        daily_data = IndividualWeekReportGenerator.aggregate_by_day_individual(player_sessions)
        player_totals = IndividualWeekReportGenerator.calculate_totals(player_sessions)
        position_avg = IndividualWeekReportGenerator.calculate_average(same_position_sessions)
        team_avg = IndividualWeekReportGenerator.calculate_average(team_sessions)
        
        # Create figure
        fig = plt.figure(figsize=(20, 14), facecolor=IndividualWeekReportGenerator.COLORS['background'])
        
        # === HEADER ===
        header_ax = plt.axes([0.05, 0.90, 0.9, 0.27])
        IndividualWeekReportGenerator._draw_header(header_ax, player_name, position, week_start, week_end, week_number)
        
        # === MAIN TABLE ===
        table_ax = plt.axes([0.05, 0.48, 0.76, 0.46])
        IndividualWeekReportGenerator._draw_daily_table(table_ax, daily_data, player_max, player_name)

        # Daily aggregates for position and team (needed for graphs and comparison)
        position_daily = IndividualWeekReportGenerator.aggregate_by_day_average(same_position_sessions)
        team_daily = IndividualWeekReportGenerator.aggregate_by_day_average(team_sessions)
        
        # === GRAPHS ===
        graph_ax = plt.axes([0.05, 0.08, 0.6, 0.30])
        IndividualWeekReportGenerator._draw_graphs(graph_ax, daily_data, position_daily, team_daily)
        
        # === COMPARISON TABLES ===
        comparison_ax = plt.axes([0.67, 0.35, 0.26, 0.80])
        IndividualWeekReportGenerator._draw_comparison_tables(comparison_ax, daily_data, position_daily, team_daily)
        
        # === LEGEND (horizontal, alignée en bas des graphiques) ===
        # [x, y_bottom, width, height] — bottom à 0.08 = bas des graphiques
        legend_ax = plt.axes([0.7, 0.08, 0.10, 0.20])
        legend_ax.axis('off')
        legend_ax.set_xlim(0, 1)
        legend_ax.set_ylim(0, 1)
        from matplotlib.patches import Rectangle

        legend_items = [
            ('#FFA500', 'JOUEUR'),
            ('#FF0000', 'MOYENNE POSTE'),
            ('#FFFFFF', 'MOYENNE EQUIPE')
        ]

        for i, (color, label) in enumerate(legend_items):
            y = 0.75 - i * 0.30
            rect = Rectangle((0.05, y - 0.08), 0.12, 0.16,
                              facecolor=color, edgecolor='white', linewidth=0.8)
            legend_ax.add_patch(rect)
            legend_ax.text(0.22, y, label,
                           fontsize=12, color='white', va='center', fontweight='bold')
        

        # Save to bytes
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt.close(fig)
        
        # Convert to base64
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return img_base64

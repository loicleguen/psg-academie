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
        
        # Group by session_title and aggregate
        session_totals = {}
        for session in all_sessions:
            title = session.get('session_title', '')
            if title not in session_totals:
                session_totals[title] = {
                    'distance_km': 0,
                    'hsr_total': 0,  # Will calculate from speed zones
                    'power_plays': 0,
                    'impacts': 0,
                }
            
            session_totals[title]['distance_km'] += session.get('distance_km', 0)
            # Calculate HSR from speed zones 3+4+5
            hsr = (session.get('speed_zone_3_km', 0) + session.get('speed_zone_4_km', 0) + session.get('speed_zone_5_km', 0)) * 1000
            session_totals[title]['hsr_total'] += hsr
            session_totals[title]['power_plays'] += session.get('power_plays', 0)
            session_totals[title]['impacts'] += session.get('impacts', 0)
        
        # Get max values
        totals = list(session_totals.values())
        benchmarks = {
            'distance_km': max([t['distance_km'] for t in totals]) if totals else 100.0,
            'hsr_total': max([t['hsr_total'] for t in totals]) if totals else 5000.0,
            'dec_total': max([t['impacts'] for t in totals]) if totals else 100.0,
            'power_plays': max([t['power_plays'] for t in totals]) if totals else 200.0,
        }
        
        return benchmarks
    
    @staticmethod
    def calculate_personal_max_by_player(all_sessions: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Calculate personal maximum values for each player across all their sessions
        
        Args:
            all_sessions: All sessions from database
            
        Returns:
            Dictionary with player_name as key and their personal max values
        """
        if not all_sessions:
            return {}
        
        # Group by player and calculate their personal max
        player_max = {}
        
        for session in all_sessions:
            player = session.get('player_name', 'Unknown')
            if player not in player_max:
                player_max[player] = {
                    'max_distance_km': 0,
                    'max_hsr': 0,
                    'max_impacts': 0,
                    'max_power_plays': 0,
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
            player_max[player]['max_impacts'] = max(
                player_max[player]['max_impacts'],
                session.get('impacts', 0)
            )
            player_max[player]['max_power_plays'] = max(
                player_max[player]['max_power_plays'],
                session.get('power_plays', 0)
            )
        
        return player_max

    @staticmethod
    def draw_semi_gauge(ax, value: float, max_value: float, title: str, percentage: float):
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
        ax.text(0.5, 0.15, f'{int(value)}', 
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
        ax.text(0.9, -0.05, f'{int(max_value)}',
                ha='center', va='top',
                fontsize=8,
                color=SessionReportGenerator.COLORS['text_gray'])
        
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.1, 0.9)
        ax.axis('off')
    
    @staticmethod
    def get_color_for_percentile(value: float, percentile_33: float, percentile_66: float) -> str:
        """
        Get background color based on percentile
        
        Args:
            value: The value to evaluate
            percentile_33: 33rd percentile (bottom threshold)
            percentile_66: 66th percentile (top threshold)
            
        Returns:
            Hex color code
        """
        if value >= percentile_66:
            return SessionReportGenerator.COLORS['dark_green']
        elif value >= percentile_33:
            return SessionReportGenerator.COLORS['dark_orange']
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
        
        # Calculate totals
        total_distance = sum(s.get('distance_km', 0) for s in session_data)
        total_hsr = sum((s.get('speed_zone_3_km', 0) + s.get('speed_zone_4_km', 0) + s.get('speed_zone_5_km', 0)) * 1000 for s in session_data)
        total_dec = sum(s.get('impacts', 0) for s in session_data)
        total_pp = sum(s.get('power_plays', 0) for s in session_data)
        
        # Get benchmarks
        benchmarks = SessionReportGenerator.calculate_benchmarks(all_sessions)
        personal_max_by_player = SessionReportGenerator.calculate_personal_max_by_player(all_sessions)

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
            ax1, total_distance * 1000, benchmarks['distance_km'] * 1000,
            'DISTANCE ÉQUIPE', pct_distance
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
        
        # Calculate percentiles for color coding
        distances = [s.get('distance_km', 0) for s in session_data]
        hsrs = [s.get('sprint_distance_m', 0) for s in session_data]
        decs = [s.get('impacts', 0) for s in session_data]
        pps = [s.get('power_plays', 0) for s in session_data]
        
        p33_dist = np.percentile(distances, 33) if distances else 0
        p66_dist = np.percentile(distances, 66) if distances else 0
        p33_hsr = np.percentile(hsrs, 33) if hsrs else 0
        p66_hsr = np.percentile(hsrs, 66) if hsrs else 0
        p33_dec = np.percentile(decs, 33) if decs else 0
        p66_dec = np.percentile(decs, 66) if decs else 0
        p33_pp = np.percentile(pps, 33) if pps else 0
        p66_pp = np.percentile(pps, 66) if pps else 0
        
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
            vmax = player.get('top_speed', 0)
            dec = player.get('impacts', 0)
            pp = player.get('power_plays', 0)
            dist_per_min = player.get('distance_per_min', 0)
            player_load = player.get('player_load', 0)
            
            # Calculate percentages
            # Get personal max for this player
            player_name = player.get('player_name', 'Unknown')
            personal_max = personal_max_by_player.get(player_name, {})
            pct_dist = (distance / personal_max.get('max_distance_km', 1) * 100) if personal_max.get('max_distance_km', 0) > 0 else 0
            pct_hsr = (hsr / personal_max.get('max_hsr', 1) * 100) if personal_max.get('max_hsr', 0) > 0 else 0
            pct_sprint = (sprint / personal_max.get('max_hsr', 1) * 100) if personal_max.get('max_hsr', 0) > 0 else 0
            pct_dec = (dec / personal_max.get('max_impacts', 1) * 100) if personal_max.get('max_impacts', 0) > 0 else 0
            pct_pp = (pp / personal_max.get('max_power_plays', 1) * 100) if personal_max.get('max_power_plays', 0) > 0 else 0
            
            # Row data
            row_data = [
                player.get('player_name', 'Unknown'),
                f"{int(duration_min)}",
                f"{int(distance * 1000)}",  # Convert km to meters
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
                "40%",  # Placeholder
                f"{int(player_load / duration_min * 100)}%" if duration_min > 0 else "0%"
            ]
            
            # Determine colors for specific columns
            colors = [SessionReportGenerator.COLORS['background']] * num_cols
            colors[2] = SessionReportGenerator.get_color_for_percentile(distance, p33_dist, p66_dist)
            colors[4] = SessionReportGenerator.get_color_for_percentile(hsr, p33_hsr, p66_hsr)
            colors[9] = SessionReportGenerator.get_color_for_percentile(dec, p33_dec, p66_dec)
            colors[11] = SessionReportGenerator.get_color_for_percentile(pp, p33_pp, p66_pp)
            
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
                
                table_ax.text(
                    x_text, y + row_height/2, value,
                    ha=alignment, va='center',
                    fontsize=7,
                    color=SessionReportGenerator.COLORS['text_white']
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
            'impacts': 0,
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
            
            # Add totals
            weekly_data[week_key]['distance_km'] += session.get('distance_km', 0)
            weekly_data[week_key]['sprint_distance_m'] += session.get('sprint_distance_m', 0)
            weekly_data[week_key]['impacts'] += session.get('impacts', 0)
            weekly_data[week_key]['power_plays'] += session.get('power_plays', 0)
            weekly_data[week_key]['dates'].add(date_str)
        
        # Calculate session count for each week (unique dates)
        for week_key in weekly_data:
            weekly_data[week_key]['session_count'] = len(weekly_data[week_key]['dates'])
        
        # Find max AVERAGE per session across all weeks
        max_avg_distance = 0
        max_avg_hsr = 0
        max_avg_impacts = 0
        max_avg_pp = 0
        
        for week_key, data in weekly_data.items():
            session_count = data['session_count']
            if session_count > 0:
                avg_dist = data['distance_km'] / session_count
                avg_hsr = data['sprint_distance_m'] / session_count
                avg_imp = data['impacts'] / session_count
                avg_pp = data['power_plays'] / session_count
                
                max_avg_distance = max(max_avg_distance, avg_dist)
                max_avg_hsr = max(max_avg_hsr, avg_hsr)
                max_avg_impacts = max(max_avg_impacts, avg_imp)
                max_avg_pp = max(max_avg_pp, avg_pp)
        
        return {
            'distance_km': max_avg_distance,
            'hsr_total': max_avg_hsr,
            'dec_total': max_avg_impacts,
            'power_plays': max_avg_pp
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
                    'impacts': 0,
                    'power_plays': 0,
                    'top_speed': 0,
                    'session_dates': set(),  # Track unique dates
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
            player_totals[player]['impacts'] += session.get('impacts', 0)
            player_totals[player]['power_plays'] += session.get('power_plays', 0)
            player_totals[player]['top_speed'] = max(player_totals[player]['top_speed'], session.get('top_speed', 0))
            # Add date to set (only unique dates will be counted)
            player_totals[player]['session_dates'].add(session.get('date', ''))
        
        # Convert set of dates to count
        result = []
        for player_name, data in player_totals.items():
            data['session_count'] = len(data['session_dates'])
            del data['session_dates']  # Remove the set, keep only the count
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
                'impacts': 0, 'power_plays': 0, 'top_speed': 0.0,
                'player_count': set()
            }
            for s in sessions:
                totals['duration']         += s.get('duration', 0)
                totals['distance_km']      += s.get('distance_km', 0)
                totals['sprint_distance_m']+= s.get('sprint_distance_m', 0)
                totals['impacts']          += s.get('impacts', 0)
                totals['power_plays']      += s.get('power_plays', 0)
                totals['top_speed']         = max(totals['top_speed'], s.get('top_speed', 0))
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
                # Séparer matin et après-midi
                ma_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'MA']
                ap_sessions = [s for s in sessions if get_slot(s.get('session_title', '')) == 'AP']
                # Sessions sans marqueur → rattacher à l'après-midi (ou matin si pas d'AM)
                other = [s for s in sessions if get_slot(s.get('session_title', '')) == '']
                if has_ap:
                    ap_sessions += other
                else:
                    ma_sessions += other
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
        personal_max = SessionReportGenerator.calculate_personal_max_by_player(all_sessions)
        
        # Create figure
        fig = plt.figure(figsize=(16, 20), facecolor=WeeklyReportGenerator.COLORS['background'])
        
        # === HEADER === (use plt.axes like session report)
        header_ax = plt.axes([0.05, 0.83, 0.9, 0.15])
        WeeklyReportGenerator._draw_header(header_ax, team_name, week_number, year, len(session_data))
        
        # === GAUGES === (below header)
        gauge_ax = plt.axes([0.05, 0.68, 0.9, 0.12])
        # Calculate number of unique sessions (dates)
        unique_dates = set(s.get("session_date", s.get("date")) for s in session_data)
        session_count = len(unique_dates)
        WeeklyReportGenerator._draw_gauges(gauge_ax, player_data, weekly_benchmarks, session_count)
        # === PLAYER TABLE === (main table)
        table_ax = plt.axes([0.05, 0.4, 0.9, 0.3])
        WeeklyReportGenerator._draw_player_table(table_ax, player_data, weekly_benchmarks, personal_max)
        
        # === DAILY TABLE === (bottom left)
        daily_table_ax = plt.axes([0.05, 0.12, 0.55, 0.25])
        WeeklyReportGenerator._draw_daily_table(daily_table_ax, day_data, weekly_benchmarks)
        
        # === TREND GRAPH === (bottom right)
        graph_ax = plt.axes([0.65, 0.12, 0.30, 0.25])
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
        total_impacts = sum(p['impacts'] for p in player_data)
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
            ('DISTANCE ÉQUIPE', avg_distance, benchmark_distance, pct_distance),
            ('HSR ÉQUIPE', avg_hsr, benchmark_hsr, pct_hsr),
            ('DEC ÉQUIPE', avg_impacts, benchmark_dec, pct_dec),
            ('POWERPLAY ÉQUIPE', avg_pp, benchmark_pp, pct_pp)
        ]
        
        for i, (title, value, max_value, percentage) in enumerate(gauges):
            # Create a sub-axis for each gauge
            gauge_ax = ax.inset_axes([i * 0.25, 0.3, 0.25, 1])
            # Use the same draw_semi_gauge function as session report
            SessionReportGenerator.draw_semi_gauge(gauge_ax, value, max_value, title, percentage)
    

    @staticmethod
    def _draw_player_table(ax, player_data, benchmarks, personal_max):
        """Draw complete player table with all columns and color coding"""
        ax.axis('off')
        ax.set_xlim(0, 15)
        ax.set_ylim(0, max(len(player_data) + 2, 10))
        
        # Calculate percentiles for color coding
        if player_data:
            distances = [p['distance_km'] for p in player_data]
            hsrs = [p['sprint_distance_m'] for p in player_data]
            impacts_list = [p['impacts'] for p in player_data]
            pp_list = [p['power_plays'] for p in player_data]
            
            import numpy as np
            dist_p33, dist_p66 = np.percentile(distances, [33, 66]) if distances else (0, 0)
            hsr_p33, hsr_p66 = np.percentile(hsrs, [33, 66]) if hsrs else (0, 0)
            imp_p33, imp_p66 = np.percentile(impacts_list, [33, 66]) if impacts_list else (0, 0)
            pp_p33, pp_p66 = np.percentile(pp_list, [33, 66]) if pp_list else (0, 0)
        
        # Headers
        headers = ['JOUEUR', 'MINUTES', 'DISTANCE', '%DIST', 'HSR', '%HSR', 'SPRINT', '%SPRINT', 'VMAX', '%VMAX', 'DEC', '%DEC', 'POWER PLAT', '%PP', 'VOL', 'INT', 'NB SEANCES']
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
            distance = int(player['distance_km'] * 1000)  # Convert to meters
            hsr = int(player['sprint_distance_m'])
            impacts = player['impacts']
            pp = player['power_plays']
            pmax = player['power_score']
            sessions = player['session_count']
            
            # Calculate percentages (simplified for now)
            # Get personal max for this player
            player_name = player['player_name']
            player_personal_max = personal_max.get(player_name, {})
            personal_max_dist = player_personal_max.get('max_distance_km', 1) * 1000  # Convert to meters
            personal_max_hsr = player_personal_max.get('max_hsr', 1)
            personal_max_impacts = player_personal_max.get('max_impacts', 1)
            personal_max_pp = player_personal_max.get('max_power_plays', 1)
            
            # Calculate average per session
            avg_dist_per_session = distance / sessions if sessions > 0 else 0
            avg_hsr_per_session = hsr / sessions if sessions > 0 else 0
            avg_impacts_per_session = impacts / sessions if sessions > 0 else 0
            avg_pp_per_session = pp / sessions if sessions > 0 else 0
            
            # Calculate percentages: (Average per session) / (Personal max) * 100
            dist_pct = int((avg_dist_per_session / personal_max_dist) * 100) if personal_max_dist > 0 else 0
            hsr_pct = int((avg_hsr_per_session / personal_max_hsr) * 100) if personal_max_hsr > 0 else 0
            spr_pct = hsr_pct  # Same as HSR for sprint distance
            pmax_pct = int((pmax / 10) * 100) if pmax > 0 else 0  # Simplified
            dec_pct = int((avg_impacts_per_session / personal_max_impacts) * 100) if personal_max_impacts > 0 else 0
            pp_pct = int((avg_pp_per_session / personal_max_pp) * 100) if personal_max_pp > 0 else 0
            
            # Calculate VOL and INT as percentages (like Excel)
            # VOL% = average distance per session as percentage of benchmark distance
            avg_distance_per_session = player['distance_km'] / sessions if sessions > 0 else 0
            vol_pct = int((avg_distance_per_session / benchmarks.get('distance_km', 100)) * 100) if benchmarks.get('distance_km', 0) > 0 else 0
            
            # INT% = average intensity per session as percentage of benchmark
            avg_hsr_per_session = player['sprint_distance_m'] / sessions if sessions > 0 else 0
            avg_impacts_per_session = impacts / sessions if sessions > 0 else 0
            avg_pp_per_session = pp / sessions if sessions > 0 else 0
            intensity_pct = int((avg_hsr_per_session / benchmarks.get('hsr_total', 5000) + 
                                avg_impacts_per_session / benchmarks.get('dec_total', 100) + 
                                avg_pp_per_session / benchmarks.get('power_plays', 200)) / 3 * 100)
            
            # Get colors based on percentiles
            dist_color = SessionReportGenerator.get_color_for_percentile(player['distance_km'], dist_p33, dist_p66)
            hsr_color = SessionReportGenerator.get_color_for_percentile(player['sprint_distance_m'], hsr_p33, hsr_p66)
            imp_color = SessionReportGenerator.get_color_for_percentile(impacts, imp_p33, imp_p66)
            pp_color = SessionReportGenerator.get_color_for_percentile(pp, pp_p33, pp_p66)
            
            row_data = [
                (player['player_name'][:20], None, 'center'),
                (str(minutes), None, 'center'),
                (str(distance), dist_color, 'center'),
                (f'{dist_pct}%', None, 'center'),
                (str(hsr), hsr_color, 'center'),
                (f'{hsr_pct}%', None, 'center'),
                (str(hsr), hsr_color, 'center'),
                (f'{spr_pct}%', None, 'center'),
                (f'{pmax:.1f}', None, 'center'),
                (f'{pmax_pct}%', None, 'center'),
                (str(impacts), imp_color, 'center'),
                (f'{dec_pct}%', None, 'center'),
                (str(pp), pp_color, 'center'),
                (f'{pp_pct}%', None, 'center'),
                (f'{vol_pct}%', None, 'center'),
                (f'{intensity_pct}%', None, 'center'),
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
                text_color = WeeklyReportGenerator.COLORS['text_white'] if bgcolor else WeeklyReportGenerator.COLORS['text_white']
                ax.text(x_pos + (0 if align == 'left' else width/2), y, value,
                       ha=align, va='center', fontsize=6, color=text_color)
                x_pos += width
    
    @staticmethod
    def _draw_daily_table(ax, day_data, benchmarks):
        """Draw daily breakdown table with borders"""
        import numpy as np
        ax.axis('off')
        ax.set_xlim(-0.1, 15.1)
        ax.set_ylim(0, 11)

        from matplotlib.patches import Rectangle
        HEADER_BG = WeeklyReportGenerator.COLORS['header_bg']
        ROW_BG    = WeeklyReportGenerator.COLORS['background']
        WHITE     = WeeklyReportGenerator.COLORS['text_white']
        BORDER    = '#4a5568'

        def draw_cell(x, y, w=1, h=0.45, bg=ROW_BG, border=BORDER):
            r = Rectangle((x, y - h/2), w, h, facecolor=bg, edgecolor=border, linewidth=0.5)
            ax.add_patch(r)

        def col_x(i):
            return 0 if i == 0 else i + 1

        def col_w(i):
            return 2 if i == 0 else 1

        # ── Header ────────────────────────────────────────────────────────────
        headers = ['JOUR', 'MIN', 'DIST', '%DIST', 'HSR', '%HSR',
                   'DEC', '%DEC', 'PP', '%PP', 'VOL', 'INT', 'VOLUME', 'INTENSITE']
        for i, h in enumerate(headers):
            draw_cell(col_x(i), 10.25, w=col_w(i), bg=HEADER_BG, border='white')
            ax.text(col_x(i) + col_w(i)/2, 10.25, h, ha='center', va='center',
                    fontsize=7, fontweight='bold', color=WHITE)

        # ── Data rows ─────────────────────────────────────────────────────────
        DAY_BASE = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE']
        # Construire la liste ordonnée des clés (jour seul, puis MAx2, puis AP)
        ordered_keys = []
        for base in DAY_BASE:
            if base in day_data:
                ordered_keys.append(base)
            if f'{base} MA' in day_data:
                ordered_keys.append(f'{base} MA')
            if f'{base} AP' in day_data:
                ordered_keys.append(f'{base} AP')

        row_y = 9.7

        # Accumulateurs pour TOTAL et MONOTONIE
        all_minutes, all_distance, all_hsr, all_impacts, all_pp = [], [], [], [], []
        all_vol, all_int_ = [], []

        for day in ordered_keys:
            data = day_data[day]
            # Libellé affiché : 'MERCREDI' → 'MER', 'MARDI MA' → 'MAR MA'
            parts = day.split(' ', 1)
            label = parts[0][:3] + (f' {parts[1]}' if len(parts) > 1 else '')
            minutes  = data['duration'] // 60
            distance = int(data['distance_km'] * 1000)
            hsr      = int(data['sprint_distance_m'])
            impacts  = int(data['impacts'])
            pp       = int(data['power_plays'])

            # VOL% = distance / benchmark_distance * 100
            vol_pct = int((data['distance_km'] / benchmarks.get('distance_km', 1)) * 100)                       if benchmarks.get('distance_km', 0) > 0 else 0
            # INT% = moyenne(HSR%, DEC%, PP%)
            hsr_p = (hsr / benchmarks.get('hsr_total', 1)) * 100 if benchmarks.get('hsr_total', 0) > 0 else 0
            dec_p = (impacts / benchmarks.get('dec_total', 1)) * 100 if benchmarks.get('dec_total', 0) > 0 else 0
            pp_p  = (pp / benchmarks.get('power_plays', 1)) * 100 if benchmarks.get('power_plays', 0) > 0 else 0
            int_pct = int((hsr_p + dec_p + pp_p) / 3)

            # VOLUME = (vol_pct / minutes) * 100
            volume_val    = round((vol_pct / minutes) * 100, 1) if minutes else 0
            # INTENSITE = (int_pct / minutes) * 100
            intensite_val = round((int_pct / minutes) * 100, 1) if minutes else 0

            all_minutes.append(minutes);  all_distance.append(distance)
            all_hsr.append(hsr);          all_impacts.append(impacts)
            all_pp.append(pp);            all_vol.append(vol_pct)
            all_int_.append(int_pct)

            row = [label, minutes, distance, '100%', hsr, '100%',
                   impacts, '100%', pp, '100%',
                   f'{vol_pct}%', f'{int_pct}%',
                   f'{volume_val}%', f'{intensite_val}%']

            for i, val in enumerate(row):
                draw_cell(col_x(i), row_y, w=col_w(i))
                ax.text(col_x(i) + col_w(i)/2, row_y, str(val), ha='center', va='center',
                        fontsize=7, color=WHITE)
            row_y -= 0.5

        # ── MONOTONIE ─────────────────────────────────────────────────────────
        row_y -= 0.1
        monotonie = (np.mean(all_distance) / np.std(all_distance))                     if len(all_distance) > 1 and np.std(all_distance) > 0 else 0
        mono_row = ['MONOTONIE', f'{monotonie:.2f}'] + [''] * 12
        for i, val in enumerate(mono_row):
            draw_cell(col_x(i), row_y, w=col_w(i), bg='#2d3748')
            ax.text(col_x(i) + col_w(i)/2, row_y, str(val), ha='center', va='center',
                    fontsize=7, fontweight='bold', color=WHITE)
        row_y -= 0.5

        # ── TOTAL ─────────────────────────────────────────────────────────────
        tot_min  = sum(all_minutes)
        tot_dist = sum(all_distance)
        tot_hsr  = sum(all_hsr)
        tot_imp  = sum(all_impacts)
        tot_pp   = sum(all_pp)
        tot_vol  = sum(all_vol)
        tot_int  = sum(all_int_)
        tot_volume    = round((tot_vol / tot_min) * 100, 1) if tot_min else 0
        tot_intensite = round((tot_int / tot_min) * 100, 1) if tot_min else 0

        total_row = ['TOTAL', tot_min, tot_dist, '', tot_hsr, '',
                     tot_imp, '', tot_pp, '',
                     f'{tot_vol}%', f'{tot_int}%',
                     f'{tot_volume}%', f'{tot_intensite}%']
        for i, val in enumerate(total_row):
            draw_cell(col_x(i), row_y, w=col_w(i), bg='#2d3748')
            ax.text(col_x(i) + col_w(i)/2, row_y, str(val), ha='center', va='center',
                    fontsize=7, fontweight='bold', color=WHITE)
        row_y -= 0.5

        # ── OBJECTIF ──────────────────────────────────────────────────────────
        obj_row = ['OBJECTIF', 297, 28384, '250%', 2700, '150%',
                   86, '180%', 120, '250%', '', '', '85%', '95%']
        for i, val in enumerate(obj_row):
            draw_cell(col_x(i), row_y, w=col_w(i), bg='#2d3748')
            ax.text(col_x(i) + col_w(i)/2, row_y, str(val), ha='center', va='center',
                    fontsize=7, fontweight='bold', color=WHITE)
    
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
            dec_pct = (data['impacts'] / benchmarks.get('dec_total', 100)) * 100 if benchmarks.get('dec_total', 0) > 0 else 0
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
        max_vmax = max((s.get('top_speed', 0) for s in all_sessions), default=0)
        max_dec = max((s.get('impacts', 0) for s in all_sessions), default=0)
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
                totals['dec']          += s.get('impacts', 0)
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
                if has_ap:
                    ap_sessions += other
                else:
                    ma_sessions += other
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
            day_player_data[key][player_name]['dec'] += session.get('impacts', 0)
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
        total_dec = sum(s.get('impacts', 0) for s in session_data)
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
        ax.set_ylim(0, 12)
        
        from matplotlib.patches import Rectangle
        import numpy as np
        
        # Headers
        headers = ['JOUR', 'MINUTES', 'DISTANCE', '%DIST', 'HSR', '%HSR', 'SPRINT', '%SPRINT', 'VMAX', '%VMAX', 'DEC', '%DEC', 'POWER PLAY', '%PP', 'PLAYER LOAD']
        col_widths = [1.5, 0.8, 0.9, 0.7, 0.8, 0.7, 0.8, 0.7, 0.7, 0.7, 0.7, 0.7, 1.0, 0.7, 1.2]
        
        x_pos = 0
        y = 11
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
        max_vmax = max((daily_data[day].get('vmax', 0) for day in days_order), default=0)
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
                distance = int(day_info['distance'])
                hsr = int(day_info['hsr'])
                sprint = int(day_info['sprint'])
                vmax = day_info['vmax']
                dec = day_info['dec']
                pp = day_info['pp']
                pl = day_info['player_load']
                
                # Calculate percentages
                dist_pct = int((distance / player_max['distance'] * 100)) if player_max['distance'] > 0 else 0
                hsr_pct = int((hsr / player_max['hsr'] * 100)) if player_max['hsr'] > 0 else 0
                sprint_pct = int((sprint / player_max['sprint'] * 100)) if player_max['sprint'] > 0 else 0
                vmax_pct = int((vmax / player_max['vmax'] * 100)) if player_max['vmax'] > 0 else 0
                dec_pct = int((dec / player_max['dec'] * 100)) if player_max['dec'] > 0 else 0
                pp_pct = int((pp / player_max['pp'] * 100)) if player_max['pp'] > 0 else 0
                
                # Color coding based on percentages
                dist_color = SessionReportGenerator.COLORS['green'] if dist_pct >= 50 else (SessionReportGenerator.COLORS['orange'] if dist_pct >= 30 else SessionReportGenerator.COLORS['red'])
                hsr_color = SessionReportGenerator.COLORS['green'] if hsr_pct >= 50 else (SessionReportGenerator.COLORS['orange'] if hsr_pct >= 30 else SessionReportGenerator.COLORS['red'])
                sprint_color = SessionReportGenerator.COLORS['green'] if sprint_pct >= 50 else (SessionReportGenerator.COLORS['orange'] if sprint_pct >= 30 else SessionReportGenerator.COLORS['red'])
                
                row_data = [
                    (_day_label(day), None, 'center'),
                    (str(minutes), None, 'center'),
                    (str(distance), dist_color, 'center'),
                    (f'{dist_pct}%', None, 'center'),
                    (str(hsr), hsr_color, 'center'),
                    (f'{hsr_pct}%', None, 'center'),
                    (str(sprint), sprint_color, 'center'),
                    (f'{sprint_pct}%', None, 'center'),
                    (f'{vmax:.1f}', None, 'center'),
                    (f'{vmax_pct}%', None, 'center'),
                    (str(dec), None, 'center'),
                    (f'{dec_pct}%', None, 'center'),
                    (str(pp), None, 'center'),
                    (f'{pp_pct}%', None, 'center'),
                    (f'{pl:.1f}', None, 'center')
                ]
            
            x_pos = 0
            for (value, bgcolor, align), width in zip(row_data, col_widths):
                if bgcolor:
                    rect = Rectangle((x_pos, y-0.4), width, 0.8, 
                                   facecolor=bgcolor, edgecolor='#4a5568', linewidth=0.5)
                else:
                    rect = Rectangle((x_pos, y-0.4), width, 0.8, 
                                   facecolor=IndividualWeekReportGenerator.COLORS['background'], 
                                   edgecolor='#4a5568', linewidth=0.5)
                ax.add_patch(rect)
                
                text_color = IndividualWeekReportGenerator.COLORS['text_white']
                ax.text(x_pos + width/2, y, value,
                       ha='center', va='center', fontsize=7, color=text_color)
                x_pos += width
        
        # TOTAL row
        y -= 0.3
        total_row_data = [
            ('TOTAL', None, 'center'),
            (str(total_minutes), None, 'center'),
            (str(int(total_distance)), None, 'center'),
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
            rect = Rectangle((x_pos, y-0.4), width, 0.8, 
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
            rect = Rectangle((x_pos, y-0.4), width, 0.8, 
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
                rect = Rectangle((x_pos, y-0.4), width, 0.8, 
                               facecolor=bgcolor, edgecolor='#4a5568', linewidth=0.5)
            else:
                rect = Rectangle((x_pos, y-0.4), width, 0.8, 
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
                distance = int(vals.get('distance', 0))
                hsr = int(vals.get('hsr', 0))
                sprint = int(vals.get('sprint', 0))
                vmax = vals.get('vmax', 0)
                dec = int(vals.get('dec', 0))
                pp = int(vals.get('pp', 0))
                load = vals.get('player_load', 0)

                row_values = [_daylabel(day), f'{distance}', f'{hsr}', f'{sprint}', f'{vmax:.1f}',
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
            max_vmax = max((data_daily.get(d, {}).get('vmax', 0) for d in days_order), default=0)
            total_dec = sum(int(data_daily.get(d, {}).get('dec', 0)) for d in days_order)
            total_pp = sum(int(data_daily.get(d, {}).get('pp', 0)) for d in days_order)
            total_load = sum(float(data_daily.get(d, {}).get('player_load', 0)) for d in days_order)

            totals = ['TOTAL', f'{total_distance}', f'{total_hsr}', f'{total_sprint}', f'{max_vmax:.1f}',
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
        table_ax = plt.axes([0.05, 0.50, 0.76, 0.42])
        IndividualWeekReportGenerator._draw_daily_table(table_ax, daily_data, player_max, player_name)

        # Daily aggregates for position and team (needed for graphs and comparison)
        position_daily = IndividualWeekReportGenerator.aggregate_by_day_average(same_position_sessions)
        team_daily = IndividualWeekReportGenerator.aggregate_by_day_average(team_sessions)
        
        # === GRAPHS ===
        graph_ax = plt.axes([0.05, 0.1, 0.6, 0.35])
        IndividualWeekReportGenerator._draw_graphs(graph_ax, daily_data, position_daily, team_daily)
        
        # === COMPARISON TABLES ===
        comparison_ax = plt.axes([0.67, 0.35, 0.26, 0.80])
        IndividualWeekReportGenerator._draw_comparison_tables(comparison_ax, daily_data, position_daily, team_daily)
        
        # === LEGEND (horizontal, alignée en bas des graphiques) ===
        # [x, y_bottom, width, height] — bottom à 0.10 = bas des graphiques
        legend_ax = plt.axes([0.7, 0.1, 0.10, 0.20])
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

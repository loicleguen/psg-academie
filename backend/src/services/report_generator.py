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
            match_info = session_title.split('/')[-1].strip() if '/' in session_title else 'MATCH'
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
                    'sprint_distance_m': 0,
                    'power_plays': 0,
                    'impacts': 0,
                }
            
            session_totals[title]['distance_km'] += session.get('distance_km', 0)
            session_totals[title]['sprint_distance_m'] += session.get('sprint_distance_m', 0)
            session_totals[title]['power_plays'] += session.get('power_plays', 0)
            session_totals[title]['impacts'] += session.get('impacts', 0)
        
        # Get max values
        totals = list(session_totals.values())
        benchmarks = {
            'distance_km': max([t['distance_km'] for t in totals]) if totals else 100.0,
            'hsr_total': max([t['sprint_distance_m'] for t in totals]) if totals else 5000.0,
            'dec_total': max([t['impacts'] for t in totals]) if totals else 100.0,
            'power_plays': max([t['power_plays'] for t in totals]) if totals else 200.0,
        }
        
        return benchmarks
    
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
        
        # Value arc (darker gray)
        angle = 180 * (value / max_value) if max_value > 0 else 0
        wedge_fill = Wedge(
            (0.5, 0), 0.4, 0, angle,
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
        session_title: str
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
        total_hsr = sum(s.get('sprint_distance_m', 0) for s in session_data)
        total_dec = sum(s.get('impacts', 0) for s in session_data)
        total_pp = sum(s.get('power_plays', 0) for s in session_data)
        
        # Get benchmarks
        benchmarks = SessionReportGenerator.calculate_benchmarks(all_sessions)
        
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
        
        header_ax.text(0.9, info_y + 0.15, 'MATCH',
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
        for row_idx, player in enumerate(session_data):
            y = 1 - (row_idx + 2) * row_height
            
            # Calculate player stats
            duration_min = player.get('duration', 0) / 60
            distance = player.get('distance_km', 0)
            hsr = player.get('sprint_distance_m', 0)
            sprint = hsr  # Using HSR as sprint for now
            vmax = player.get('top_speed', 0)
            dec = player.get('impacts', 0)
            pp = player.get('power_plays', 0)
            dist_per_min = player.get('distance_per_min', 0)
            player_load = player.get('player_load', 0)
            
            # Calculate percentages
            pct_dist = (distance / total_distance * 100) if total_distance > 0 else 0
            pct_hsr = (hsr / total_hsr * 100) if total_hsr > 0 else 0
            pct_sprint = pct_hsr
            pct_dec = (dec / total_dec * 100) if total_dec > 0 else 0
            pct_pp = (pp / total_pp * 100) if total_pp > 0 else 0
            
            # Row data
            row_data = [
                player.get('player_name', 'Unknown'),
                f"{int(duration_min)}",
                f"{int(distance * 1000)}",  # Convert to meters
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

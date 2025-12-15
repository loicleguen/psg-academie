import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any
import pandas as pd
from io import BytesIO
import base64


class CatapultGraphGenerator:
    """Generate graphs and visualizations from Catapult GPS data"""
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 6)
    
    @staticmethod
    def generate_player_comparison(
        session_data: List[Dict[str, Any]],
        metrics: List[str] = None
    ) -> Dict[str, str]:
        """
        Generate comparison graphs for multiple players
        
        Args:
            session_data: List of session dictionaries
            metrics: List of metrics to plot (default: distance, speed, load)
            
        Returns:
            Dictionary with metric names as keys and base64-encoded images as values
        """
        if metrics is None:
            metrics = ["distance_km", "top_speed", "player_load", "energy_kcal"]
        
        df = pd.DataFrame(session_data)
        graphs = {}
        
        for metric in metrics:
            if metric not in df.columns:
                continue
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Group by player and sum/max the metric
            if metric in ["top_speed", "max_acceleration", "max_deceleration"]:
                player_data = df.groupby("player_name")[metric].max().sort_values(ascending=False)
                ylabel = f"Max {metric.replace('_', ' ').title()}"
            else:
                player_data = df.groupby("player_name")[metric].sum().sort_values(ascending=False)
                ylabel = f"Total {metric.replace('_', ' ').title()}"
            
            # Plot
            bars = ax.bar(range(len(player_data)), player_data.values, color=sns.color_palette("viridis", len(player_data)))
            ax.set_xticks(range(len(player_data)))
            ax.set_xticklabels(player_data.index, rotation=45, ha='right')
            ax.set_ylabel(ylabel)
            ax.set_title(f"Player Comparison - {metric.replace('_', ' ').title()}")
            
            # Add value labels on bars
            for i, (bar, value) in enumerate(zip(bars, player_data.values)):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01 * max(player_data.values),
                       f'{value:.2f}', ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            
            # Convert to base64
            img_base64 = CatapultGraphGenerator._fig_to_base64(fig)
            graphs[metric] = img_base64
            
            plt.close(fig)
        
        return graphs
    
    @staticmethod
    def generate_speed_zones_distribution(
        session_data: Dict[str, Any]
    ) -> str:
        """
        Generate pie chart showing time distribution across speed zones
        
        Args:
            session_data: Single player session data
            
        Returns:
            Base64-encoded image
        """
        zones = {
            "Zone 1 (Low)": session_data.get("speed_zone_1_secs", 0),
            "Zone 2": session_data.get("speed_zone_2_secs", 0),
            "Zone 3": session_data.get("speed_zone_3_secs", 0),
            "Zone 4": session_data.get("speed_zone_4_secs", 0),
            "Zone 5 (Sprint)": session_data.get("speed_zone_5_secs", 0),
        }
        
        # Filter out zero values
        zones = {k: v for k, v in zones.items() if v > 0}
        
        if not zones:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
        wedges, texts, autotexts = ax.pie(
            zones.values(),
            labels=zones.keys(),
            autopct='%1.1f%%',
            colors=colors[:len(zones)],
            startangle=90
        )
        
        # Improve text readability
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title(f"Speed Zones Distribution - {session_data.get('player_name', 'Unknown')}")
        
        plt.tight_layout()
        img_base64 = CatapultGraphGenerator._fig_to_base64(fig)
        plt.close(fig)
        
        return img_base64
    
    @staticmethod
    def generate_intensity_timeline(
        player_sessions: List[Dict[str, Any]]
    ) -> str:
        """
        Generate line chart showing intensity over different splits
        
        Args:
            player_sessions: All sessions for one player (different splits)
            
        Returns:
            Base64-encoded image
        """
        df = pd.DataFrame(player_sessions)
        df = df.sort_values("split_start_time")
        
        # Calculate intensity (player load per minute)
        df["intensity"] = df.apply(
            lambda row: row["player_load"] / (row["duration"] / 60) if row["duration"] > 0 else 0,
            axis=1
        )
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = range(len(df))
        ax.plot(x, df["intensity"].values, marker='o', linewidth=2, markersize=8, color='#e74c3c')
        ax.fill_between(x, df["intensity"].values, alpha=0.3, color='#e74c3c')
        
        ax.set_xticks(x)
        ax.set_xticklabels(df["split_name"].values, rotation=45, ha='right')
        ax.set_xlabel("Split")
        ax.set_ylabel("Intensity (Player Load / min)")
        ax.set_title(f"Training Intensity Timeline - {df.iloc[0]['player_name']}")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        img_base64 = CatapultGraphGenerator._fig_to_base64(fig)
        plt.close(fig)
        
        return img_base64
    
    @staticmethod
    def generate_multi_metric_radar(
        session_data: Dict[str, Any],
        player_avg: Dict[str, float] = None
    ) -> str:
        """
        Generate radar chart comparing player performance to team average
        
        Args:
            session_data: Player session data
            player_avg: Team average values for comparison (optional)
            
        Returns:
            Base64-encoded image
        """
        from math import pi
        
        # Select metrics for radar chart
        metrics = {
            "Distance": session_data.get("distance_km", 0),
            "Top Speed": session_data.get("top_speed", 0),
            "Player Load": session_data.get("player_load", 0) / 100,  # Scale down
            "Sprint Dist.": session_data.get("sprint_distance_m", 0) / 100,  # Scale down
            "Max Accel.": session_data.get("max_acceleration", 0),
        }
        
        categories = list(metrics.keys())
        values = list(metrics.values())
        
        # Number of variables
        N = len(categories)
        
        # Compute angle for each axis
        angles = [n / float(N) * 2 * pi for n in range(N)]
        values += values[:1]  # Complete the circle
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Plot player data
        ax.plot(angles, values, 'o-', linewidth=2, label=session_data.get("player_name", "Player"), color='#3498db')
        ax.fill(angles, values, alpha=0.25, color='#3498db')
        
        # Plot team average if provided
        if player_avg:
            avg_values = [player_avg.get(k, 0) for k in metrics.keys()]
            avg_values += avg_values[:1]
            ax.plot(angles, avg_values, 'o-', linewidth=2, label="Team Average", color='#95a5a6')
            ax.fill(angles, avg_values, alpha=0.1, color='#95a5a6')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_title(f"Performance Radar - {session_data.get('player_name', 'Unknown')}", pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)
        
        plt.tight_layout()
        img_base64 = CatapultGraphGenerator._fig_to_base64(fig)
        plt.close(fig)
        
        return img_base64
    
    @staticmethod
    def generate_distance_breakdown(
        session_data: Dict[str, Any]
    ) -> str:
        """
        Generate stacked bar chart showing distance breakdown by speed zones
        
        Args:
            session_data: Player session data
            
        Returns:
            Base64-encoded image
        """
        zones = {
            "Zone 1": session_data.get("speed_zone_1_km", 0),
            "Zone 2": session_data.get("speed_zone_2_km", 0),
            "Zone 3": session_data.get("speed_zone_3_km", 0),
            "Zone 4": session_data.get("speed_zone_4_km", 0),
            "Zone 5": session_data.get("speed_zone_5_km", 0),
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
        bottom = 0
        
        for (zone, distance), color in zip(zones.items(), colors):
            ax.bar(0, distance, bottom=bottom, label=zone, color=color, width=0.5)
            if distance > 0:
                ax.text(0, bottom + distance/2, f'{distance:.2f} km', 
                       ha='center', va='center', fontweight='bold', color='white')
            bottom += distance
        
        ax.set_ylabel("Distance (km)")
        ax.set_title(f"Distance by Speed Zone - {session_data.get('player_name', 'Unknown')}")
        ax.set_xticks([])
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.set_ylim(0, bottom * 1.1)
        
        plt.tight_layout()
        img_base64 = CatapultGraphGenerator._fig_to_base64(fig)
        plt.close(fig)
        
        return img_base64
    
    @staticmethod
    def _fig_to_base64(fig) -> str:
        """Convert matplotlib figure to base64-encoded string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        return img_base64

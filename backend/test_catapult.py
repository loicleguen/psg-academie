"""
Example script to test Catapult CSV upload and graph generation
"""

import requests
import base64
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
CSV_FILE_PATH = "catapult_sample.csv"  # Replace with your CSV file path
OUTPUT_DIR = "catapult_graphs"

def upload_csv(file_path: str):
    """Upload Catapult CSV file"""
    print(f"📤 Uploading {file_path}...")
    
    url = f"{API_BASE_URL}/catapult/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Upload successful!")
        print(f"   - Session: {data['session_title']}")
        print(f"   - Players: {data['total_players']}")
        print(f"   - Records stored: {data['records_stored']}")
        print(f"   - Avg distance: {data['avg_distance_km']:.2f} km")
        print(f"   - Max speed: {data['max_top_speed']:.2f} m/s")
        return data
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def analyze_session(session_title: str):
    """Analyze a training session"""
    print(f"\n🔍 Analyzing session: {session_title}...")
    
    url = f"{API_BASE_URL}/catapult/analyze/session/{session_title}"
    response = requests.post(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analysis complete!")
        print(f"   - Total players: {data['total_players']}")
        print(f"\n   Top 3 players by distance:")
        
        players = sorted(
            data['player_comparison'],
            key=lambda x: x['distance_km'],
            reverse=True
        )[:3]
        
        for i, player in enumerate(players, 1):
            print(f"   {i}. {player['player_name']}: {player['distance_km']:.2f} km")
        
        return data
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        return None


def generate_session_graphs(session_title: str, output_dir: str = "graphs"):
    """Generate comparison graphs for all players"""
    print(f"\n📊 Generating session graphs...")
    
    url = f"{API_BASE_URL}/catapult/graphs/session/{session_title}"
    response = requests.post(url)
    
    if response.status_code == 200:
        data = response.json()
        graphs = data['graphs']
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        print(f"✅ Generated {len(graphs)} graphs!")
        
        # Save each graph
        for metric, img_base64 in graphs.items():
            filename = f"{output_dir}/session_{metric}.png"
            with open(filename, 'wb') as f:
                f.write(base64.b64decode(img_base64))
            print(f"   💾 Saved: {filename}")
        
        return True
    else:
        print(f"❌ Graph generation failed: {response.status_code}")
        return False


def generate_player_graphs(player_name: str, session_title: str = None, output_dir: str = "graphs"):
    """Generate graphs for a specific player"""
    print(f"\n📊 Generating graphs for {player_name}...")
    
    url = f"{API_BASE_URL}/catapult/graphs/player/{player_name}"
    if session_title:
        url += f"?session_title={session_title}"
    
    response = requests.post(url)
    
    if response.status_code == 200:
        data = response.json()
        graphs = data['graphs']
        
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        print(f"✅ Generated {len(graphs)} graphs!")
        
        # Save each graph
        for graph_type, img_base64 in graphs.items():
            safe_name = player_name.replace(' ', '_').lower()
            filename = f"{output_dir}/player_{safe_name}_{graph_type}.png"
            with open(filename, 'wb') as f:
                f.write(base64.b64decode(img_base64))
            print(f"   💾 Saved: {filename}")
        
        return True
    else:
        print(f"❌ Graph generation failed: {response.status_code}")
        return False


def analyze_player(player_name: str, session_title: str = None):
    """Analyze a specific player's performance"""
    print(f"\n🔍 Analyzing player: {player_name}...")
    
    url = f"{API_BASE_URL}/catapult/analyze/player/{player_name}"
    if session_title:
        url += f"?session_title={session_title}"
    
    response = requests.post(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analysis complete!")
        print(f"   - Total distance: {data['total_distance_km']:.2f} km")
        print(f"   - Peak speed: {data['peak_speed_kmh']:.2f} km/h")
        print(f"   - Avg intensity: {data['avg_intensity']:.2f}")
        print(f"   - Total energy: {data['total_energy_kcal']:.0f} kcal")
        
        if data['splits']:
            print(f"\n   Splits breakdown:")
            for split in data['splits']:
                print(f"   - {split['split_name']}: {split['distance_km']:.2f} km, "
                      f"{split['duration_min']:.0f} min, intensity {split['intensity']:.2f}")
        
        return data
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        return None


def main():
    """Main execution flow"""
    print("="*60)
    print("🏃 CATAPULT GPS DATA PROCESSOR")
    print("="*60)
    
    # 1. Upload CSV
    upload_result = upload_csv(CSV_FILE_PATH)
    if not upload_result:
        return
    
    session_title = upload_result['session_title']
    
    # 2. Analyze session
    analysis = analyze_session(session_title)
    if not analysis:
        return
    
    # 3. Generate session graphs
    generate_session_graphs(session_title, OUTPUT_DIR)
    
    # 4. Get top player
    if analysis['player_comparison']:
        top_player = sorted(
            analysis['player_comparison'],
            key=lambda x: x['distance_km'],
            reverse=True
        )[0]
        
        player_name = top_player['player_name']
        
        # 5. Analyze top player
        analyze_player(player_name, session_title)
        
        # 6. Generate player graphs
        generate_player_graphs(player_name, session_title, OUTPUT_DIR)
    
    print(f"\n{'='*60}")
    print(f"✅ All done! Graphs saved in '{OUTPUT_DIR}/' directory")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

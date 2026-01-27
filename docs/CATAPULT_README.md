# Catapult GPS Data Processing

Système automatisé pour analyser les données GPS Catapult et générer des graphiques de performance.

## 📊 Fonctionnalités

### 1. **Upload de fichiers CSV**
- Import automatique des fichiers CSV Catapult
- Parsing intelligent des données GPS
- Stockage en base de données PostgreSQL

### 2. **Détection automatique des splits**
- Identification des différentes phases d'entraînement
- Catégorisation : échauffement, 1ère mi-temps, pause, 2ème mi-temps, retour au calme
- Analyse de l'intensité par split

### 3. **Génération de graphiques**
- **Comparaison entre joueurs** : distance, vitesse max, charge, énergie
- **Distribution par zones de vitesse** : temps passé dans chaque zone
- **Timeline d'intensité** : évolution de la charge sur l'entraînement
- **Breakdown de distance** : répartition par zones de vitesse
- **Radar de performance** : vue d'ensemble multi-métriques

## 🚀 Utilisation

### Upload d'un fichier CSV

```bash
POST /catapult/upload
Content-Type: multipart/form-data

file: [votre_fichier.csv]
```

**Réponse:**
```json
{
  "session_title": "SEANCE N3 / 20 NOVEMBRE 2025",
  "session_date": "45981",
  "total_players": 12,
  "avg_distance_km": 7.2,
  "max_distance_km": 8.0,
  "avg_top_speed": 7.8,
  "max_top_speed": 9.1,
  "avg_player_load": 385.5,
  "total_duration_minutes": 91,
  "records_stored": 12,
  "filename": "catapult_data.csv"
}
```

### Analyser une session

```bash
POST /catapult/analyze/session/SEANCE%20N3%20/%2020%20NOVEMBRE%202025
```

**Réponse:**
```json
{
  "summary": {
    "session_title": "SEANCE N3 / 20 NOVEMBRE 2025",
    "total_players": 12,
    "avg_distance_km": 7.2,
    ...
  },
  "split_categories": {
    "warm-up": 0,
    "first-half": 0,
    "halftime": 0,
    "second-half": 0,
    "cool-down": 0,
    "other": 12
  },
  "player_comparison": [
    {
      "player_name": "RIBOT YOHAN",
      "distance_km": 8.012,
      "top_speed_kmh": 29.72,
      ...
    }
  ]
}
```

### Analyser un joueur

```bash
POST /catapult/analyze/player/RIBOT%20YOHAN?session_title=SEANCE%20N3%20/%2020%20NOVEMBRE%202025
```

**Réponse:**
```json
{
  "player_name": "RIBOT YOHAN",
  "session_title": "SEANCE N3 / 20 NOVEMBRE 2025",
  "total_splits": 1,
  "splits": [
    {
      "split_name": "all",
      "duration_min": 93.85,
      "distance_km": 8.012,
      "avg_speed_kmh": 5.12,
      "max_speed_kmh": 29.72,
      "intensity": 4.23
    }
  ],
  "total_distance_km": 8.012,
  "peak_speed_kmh": 29.72,
  "total_energy_kcal": 1018.28
}
```

### Générer des graphiques pour un joueur

```bash
POST /catapult/graphs/player/RIBOT%20YOHAN?session_title=SEANCE%20N3%20/%2020%20NOVEMBRE%202025
```

**Réponse:**
```json
{
  "player_name": "RIBOT YOHAN",
  "session_title": "SEANCE N3 / 20 NOVEMBRE 2025",
  "graphs": {
    "speed_zones": "base64_encoded_image...",
    "distance_breakdown": "base64_encoded_image..."
  }
}
```

### Générer des graphiques de comparaison

```bash
POST /catapult/graphs/session/SEANCE%20N3%20/%2020%20NOVEMBRE%202025
```

**Réponse:**
```json
{
  "session_title": "SEANCE N3 / 20 NOVEMBRE 2025",
  "total_players": 12,
  "graphs": {
    "distance_km": "base64_encoded_image...",
    "top_speed": "base64_encoded_image...",
    "player_load": "base64_encoded_image...",
    "energy_kcal": "base64_encoded_image...",
    "sprint_distance_m": "base64_encoded_image..."
  }
}
```

## 📝 Format des données CSV

Le système accepte les fichiers CSV exportés depuis Catapult avec les colonnes suivantes:

### Colonnes obligatoires:
- `Date`
- `Session Title`
- `Player Name`
- `Split Name`
- `Duration`
- `Distance (km)`
- `Top Speed (m/s)`
- `Player Load`

### Colonnes optionnelles:
- Zones de vitesse (1-5)
- Zones de puissance
- Zones d'accélération/décélération
- Impacts
- Fréquence cardiaque
- Et plus...

## 🎨 Types de graphiques disponibles

### 1. Comparaison entre joueurs (Bar charts)
- Distance totale parcourue
- Vitesse maximale
- Charge du joueur (Player Load)
- Énergie dépensée (kcal)
- Distance de sprint

### 2. Distribution par zones de vitesse (Pie chart)
- Temps passé dans chaque zone
- Visualisation en pourcentage

### 3. Timeline d'intensité (Line chart)
- Évolution de l'intensité sur les différents splits
- Charge par minute

### 4. Breakdown de distance (Stacked bar)
- Répartition de la distance par zone de vitesse
- Visualisation cumulée

### 5. Radar de performance
- Vue multi-métriques d'un joueur
- Comparaison avec la moyenne de l'équipe (optionnel)

## 🔧 API Endpoints complets

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/catapult/upload` | Upload un fichier CSV |
| GET | `/catapult/sessions` | Liste toutes les sessions |
| GET | `/catapult/sessions/{id}` | Récupère une session par ID |
| GET | `/catapult/sessions/title/{title}` | Sessions par titre |
| GET | `/catapult/sessions/player/{name}` | Sessions d'un joueur |
| POST | `/catapult/analyze/session/{title}` | Analyse complète d'une session |
| POST | `/catapult/analyze/player/{name}` | Analyse complète d'un joueur |
| POST | `/catapult/graphs/player/{name}` | Graphiques d'un joueur |
| POST | `/catapult/graphs/session/{title}` | Graphiques de comparaison |
| DELETE | `/catapult/sessions/{id}` | Supprime une session |
| DELETE | `/catapult/sessions/title/{title}` | Supprime toutes les sessions d'un titre |

## 💡 Exemples d'utilisation

### Avec curl

```bash
# Upload CSV
curl -X POST "http://localhost:8000/catapult/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@catapult_data.csv"

# Analyser session
curl -X POST "http://localhost:8000/catapult/analyze/session/SEANCE%20N3%20/%2020%20NOVEMBRE%202025"

# Graphiques joueur
curl -X POST "http://localhost:8000/catapult/graphs/player/RIBOT%20YOHAN" \
  -o player_graphs.json
```

### Avec Python

```python
import requests

# Upload CSV
with open('catapult_data.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/catapult/upload',
        files={'file': f}
    )
    print(response.json())

# Générer graphiques
response = requests.post(
    'http://localhost:8000/catapult/graphs/session/SEANCE N3 / 20 NOVEMBRE 2025'
)
graphs = response.json()['graphs']

# Sauvegarder les images
import base64
for metric, img_base64 in graphs.items():
    with open(f'{metric}.png', 'wb') as f:
        f.write(base64.b64decode(img_base64))
```

## 📊 Métriques trackées

- **Distance** : totale, par zone de vitesse, de sprint
- **Vitesse** : max, moyenne, distribution
- **Charge** : Player Load, intensité
- **Énergie** : dépense calorique
- **Accélérations/Décélérations** : zones, max
- **Fréquence cardiaque** : max, zones, temps en zone rouge
- **Impacts** : total, par zone de G-force
- **Power Plays** : nombre, durée

## 🎯 Workflow automatisé

1. **Export CSV depuis Catapult** → Fichier brut
2. **Upload via API** → `/catapult/upload`
3. **Parsing automatique** → Extraction des données
4. **Stockage DB** → PostgreSQL
5. **Analyse** → Détection splits, calculs
6. **Génération graphiques** → Images base64
7. **Export/Partage** → Rapports automatiques

Plus besoin de manipulation Excel manuelle! 🎉

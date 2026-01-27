# 🏃 Système Catapult GPS - Installation complète ✅

## ✅ Ce qui a été créé

### 1. **Modèles de données** ([src/models/catapult.py](backend/src/models/catapult.py))
- `CatapultSession` : Stocke toutes les données GPS d'une session
- `CatapultSessionCreate` : Schema pour créer une nouvelle session
- `ProcessedSplit` : Schema pour les splits détectés

### 2. **Services de traitement** 

#### [src/services/catapult_parser.py](backend/src/services/catapult_parser.py)
- Parse automatiquement les fichiers CSV Catapult
- Mappe 100+ colonnes vers le modèle de données
- Groupe les données par joueur
- Génère des statistiques de session

#### [src/services/split_detector.py](backend/src/services/split_detector.py)
- Détection automatique des splits (échauffement, mi-temps, pauses)
- Catégorisation intelligente basée sur les noms et l'intensité
- Analyse comparative entre joueurs
- Métriques d'intensité par split

#### [src/services/graph_generator.py](backend/src/services/graph_generator.py)
- **5 types de graphiques** générés automatiquement :
  1. Comparaison entre joueurs (bar charts)
  2. Distribution par zones de vitesse (pie charts)
  3. Timeline d'intensité (line charts)
  4. Breakdown de distance (stacked bars)
  5. Radar de performance (polar charts)
- Export en images base64 (prêt pour intégration web)

### 3. **API Endpoints** ([src/routes/catapult.py](backend/src/routes/catapult.py))

#### Upload & Stockage
- `POST /catapult/upload` - Upload CSV et parse automatiquement
- `GET /catapult/sessions` - Liste toutes les sessions
- `GET /catapult/sessions/{id}` - Récupère une session
- `GET /catapult/sessions/title/{title}` - Sessions par titre
- `GET /catapult/sessions/player/{name}` - Sessions d'un joueur

#### Analyse
- `POST /catapult/analyze/session/{title}` - Analyse complète de session
- `POST /catapult/analyze/player/{name}` - Analyse d'un joueur

#### Graphiques
- `POST /catapult/graphs/session/{title}` - Graphiques de comparaison
- `POST /catapult/graphs/player/{name}` - Graphiques individuels

#### Suppression
- `DELETE /catapult/sessions/{id}` - Supprime une session
- `DELETE /catapult/sessions/title/{title}` - Supprime par titre

### 4. **Base de données**
- Nouvelle table `catapultsession` créée automatiquement
- 35+ colonnes pour toutes les métriques Catapult
- Clé étrangère vers `player` (CASCADE delete)
- Index sur `session_title` et `player_name`

### 5. **Documentation**
- [CATAPULT_README.md](backend/CATAPULT_README.md) - Guide complet d'utilisation
- [test_catapult.py](backend/test_catapult.py) - Script de test/démo
- [catapult_sample.csv](backend/catapult_sample.csv) - Données d'exemple

### 6. **Dépendances installées**
```
pandas==2.3.3          # Parsing CSV
matplotlib==3.10.8     # Génération de graphiques
seaborn==0.13.2        # Styles de graphiques
python-multipart==0.0.20  # Upload de fichiers
```

## 🚀 Comment l'utiliser

### Démarrer le serveur
```bash
cd backend
source /home/loicleguen/holbertonschool/.venv/bin/activate
./run.sh
```

### Accéder à la documentation interactive
Ouvre ton navigateur : **http://localhost:8000/docs**

### Upload un CSV
1. Va sur `/docs`
2. Clique sur `POST /catapult/upload`
3. Clique "Try it out"
4. Upload ton fichier CSV
5. Execute

### Générer des graphiques
```bash
# Graphiques de session (comparaison joueurs)
curl -X POST "http://localhost:8000/catapult/graphs/session/SEANCE%20N3%20/%2020%20NOVEMBRE%202025"

# Graphiques d'un joueur
curl -X POST "http://localhost:8000/catapult/graphs/player/RIBOT%20YOHAN"
```

## 📊 Métriques disponibles

### Distance
- Distance totale (km)
- Distance par zone de vitesse (5 zones)
- Distance de sprint (m)
- Distance par minute

### Vitesse
- Vitesse max (m/s)
- Temps dans chaque zone de vitesse
- Distribution des vitesses

### Charge & Intensité
- Player Load
- Intensité (load/min)
- Work Ratio
- Énergie dépensée (kcal)

### Accélération/Décélération
- Max acceleration (m/s/s)
- Max deceleration (m/s/s)
- Zones d'accélération
- Zones de décélération

### Performance
- Power Score (w/kg)
- Power Plays
- Impacts (par zone de G-force)

### Cardio
- HR Max (bpm)
- HR Load
- Temps en zone rouge
- Zones de fréquence cardiaque

## 🎯 Workflow automatisé

**AVANT** (Processus manuel) ❌
1. Export CSV depuis Catapult
2. Ouvrir Excel
3. Séparer manuellement les splits
4. Créer des tableaux croisés
5. Générer des graphiques un par un
6. Copier/coller dans PowerPoint
7. **Temps : 30-60 minutes par session**

**MAINTENANT** (Automatisé) ✅
1. Export CSV depuis Catapult
2. Upload via API : `POST /catapult/upload`
3. Générer graphiques : `POST /catapult/graphs/session/{title}`
4. Télécharger les images
5. **Temps : 30 secondes** ⚡

## 🔥 Exemple complet

```python
import requests
import base64

# 1. Upload CSV
with open('catapult_data.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/catapult/upload',
        files={'file': f}
    )
    session_info = response.json()
    print(f"Session: {session_info['session_title']}")
    print(f"Players: {session_info['total_players']}")

# 2. Analyser la session
response = requests.post(
    f"http://localhost:8000/catapult/analyze/session/{session_info['session_title']}"
)
analysis = response.json()

# Top 3 joueurs par distance
top_players = sorted(
    analysis['player_comparison'],
    key=lambda x: x['distance_km'],
    reverse=True
)[:3]

for i, player in enumerate(top_players, 1):
    print(f"{i}. {player['player_name']}: {player['distance_km']:.2f} km")

# 3. Générer graphiques de session
response = requests.post(
    f"http://localhost:8000/catapult/graphs/session/{session_info['session_title']}"
)
graphs = response.json()['graphs']

# 4. Sauvegarder les images
for metric, img_base64 in graphs.items():
    with open(f'{metric}.png', 'wb') as f:
        f.write(base64.b64decode(img_base64))
    print(f"Saved: {metric}.png")

# 5. Analyser joueur spécifique
player_name = top_players[0]['player_name']
response = requests.post(
    f"http://localhost:8000/catapult/analyze/player/{player_name}"
)
player_analysis = response.json()

print(f"\n{player_name} Analysis:")
print(f"  - Distance: {player_analysis['total_distance_km']:.2f} km")
print(f"  - Peak speed: {player_analysis['peak_speed_kmh']:.2f} km/h")
print(f"  - Energy: {player_analysis['total_energy_kcal']:.0f} kcal")

# 6. Générer graphiques du joueur
response = requests.post(
    f"http://localhost:8000/catapult/graphs/player/{player_name}"
)
player_graphs = response.json()['graphs']

for graph_type, img_base64 in player_graphs.items():
    filename = f'{player_name.replace(" ", "_")}_{graph_type}.png'
    with open(filename, 'wb') as f:
        f.write(base64.b64decode(img_base64))
    print(f"Saved: {filename}")
```

## 📁 Structure créée

```
backend/
├── src/
│   ├── models/
│   │   └── catapult.py          # Modèles SQLModel
│   ├── services/
│   │   ├── catapult_parser.py   # Parser CSV
│   │   ├── split_detector.py    # Détection splits
│   │   └── graph_generator.py   # Génération graphiques
│   └── routes/
│       └── catapult.py          # Endpoints API
├── CATAPULT_README.md           # Documentation complète
├── test_catapult.py             # Script de test
├── catapult_sample.csv          # Données d'exemple
└── requirements.txt             # Dépendances mises à jour
```

## 🎨 Types de graphiques générés

### 1. Comparaison joueurs (Bar Chart)
![Exemple](https://via.placeholder.com/800x400/3498db/ffffff?text=Player+Comparison+-+Distance)
- Compare distance, vitesse, charge, énergie
- Tri automatique par performance
- Valeurs affichées sur les barres

### 2. Zones de vitesse (Pie Chart)
![Exemple](https://via.placeholder.com/600x600/2ecc71/ffffff?text=Speed+Zones+Distribution)
- Temps passé dans chaque zone
- Pourcentages automatiques
- 5 zones de couleur

### 3. Timeline intensité (Line Chart)
![Exemple](https://via.placeholder.com/800x400/e74c3c/ffffff?text=Intensity+Timeline)
- Évolution sur les splits
- Charge par minute
- Zones remplies

### 4. Distance breakdown (Stacked Bar)
![Exemple](https://via.placeholder.com/600x400/f39c12/ffffff?text=Distance+by+Speed+Zone)
- Répartition par zone
- Distances cumulées
- Valeurs en km

### 5. Radar performance (Polar Chart)
![Exemple](https://via.placeholder.com/600x600/9b59b6/ffffff?text=Performance+Radar)
- Vue multi-métriques
- Comparaison moyenne équipe
- 5-6 dimensions

## ✅ Prêt à utiliser!

Tout est configuré et prêt à l'emploi. Tu peux maintenant :
- ✅ Upload des CSV Catapult via l'API
- ✅ Analyser automatiquement les sessions
- ✅ Générer des graphiques professionnels
- ✅ Exporter les données pour rapports
- ✅ Comparer les performances des joueurs
- ✅ Tracker l'évolution dans le temps

**Plus besoin de manipulation Excel manuelle!** 🎉

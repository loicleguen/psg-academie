FROM python:3.12-slim

WORKDIR /app

# 1. Installation des outils de compilation nécessaires pour bcrypt, sqlalchemy, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Copie du fichier de dépendances d'abord (optimise le cache Docker)
COPY backend-catapult/requirements.txt .

# 3. Installation des packages Python
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copie du reste du code source
COPY backend-catapult/. .
COPY common ./common
COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

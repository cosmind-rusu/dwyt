FROM python:3.11-slim

# Instalar ffmpeg (necesario para yt-dlp convertir a MP3)
RUN apt-get update && apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requisitos primero (caching de capas Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . .

# Railway asigna el puerto via variable de entorno PORT
EXPOSE $PORT

CMD ["python", "app.py"]

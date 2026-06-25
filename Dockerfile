FROM python:3.11-slim

# Instalar ffmpeg (conversión a MP3) + deno (JS runtime para yt-dlp)
RUN apt-get update && apt-get install -y ffmpeg curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Instalar deno (JS runtime necesario para extraer YouTube)
RUN curl -fsSL https://deno.land/install.sh | sh -s -- -y
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

# Requisitos primero (caching de capas Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . .

# Railway asigna el puerto via variable de entorno PORT
EXPOSE $PORT

CMD ["python", "app.py"]

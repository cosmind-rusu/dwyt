# 🎵 dwyt — Download YouTube to MP3

Web app para descargar audio de YouTube en MP3 de alta calidad.  
Pega un link, obtén el MP3. Simple y directo.

## 🚀 Demo en vivo

Si está desplegado en Railway, abre la URL que te da Railway.

## ⚙️ Uso local

```bash
git clone https://github.com/cosmind-rusu/dwyt.git
cd dwyt

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Asegúrate de tener ffmpeg instalado
#   Ubuntu/Debian: sudo apt install ffmpeg
#   macOS: brew install ffmpeg

# Arrancar
python app.py
# → http://localhost:5000
```

## ☁️ Despliegue en Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/cosmind-rusu/dwyt)

O manualmente:

1. Sube el repo a GitHub
2. Ve a [Railway](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Railway detecta el `Dockerfile` automáticamente
4. ¡Listo! Railway te da una URL pública

### Notas para Railway
- El `Dockerfile` incluye `ffmpeg` necesario para la conversión a MP3
- Los archivos descargados se almacenan en el filesystem efímero — descárgalos inmediatamente
- Railway asigna el puerto automáticamente via la variable `PORT`

## 🔧 Tecnologías

- **Backend:** Python + Flask
- **Descargas:** yt-dlp + ffmpeg
- **Frontend:** HTML + CSS + JS vanilla (sin frameworks)
- **Despliegue:** Docker + Railway

## ⚠️ Aviso legal

Esta herramienta es para uso personal. Respeta los derechos de autor.  
Descarga solo contenido que tengas derecho a reproducir.

---

Hecho con ❤️ por [cdrusu](https://github.com/cosmind-rusu)

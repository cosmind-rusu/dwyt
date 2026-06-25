#!/usr/bin/env python3
"""
dwyt — Download YouTube to MP3 web app.
"""

import os
import re
import shutil
import subprocess
import sys
import time
import threading
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Find yt-dlp — must be accessible via subprocess
YT_DLP = shutil.which("yt-dlp") or str(Path(sys.executable).parent / "yt-dlp")
if not Path(YT_DLP).exists():
    YT_DLP = f"{sys.executable} -m yt_dlp"  # fallback: run as module

MAX_FILE_AGE = 3600  # 1 hour — clean files older than this

# ── Periodic cleanup ──────────────────────────────────────────

def cleanup_old_files():
    """Remove downloaded files older than MAX_FILE_AGE seconds."""
    while True:
        now = time.time()
        for f in DOWNLOAD_DIR.iterdir():
            if f.is_file() and (now - f.stat().st_mtime) > MAX_FILE_AGE:
                f.unlink(missing_ok=True)
        time.sleep(300)  # every 5 minutes

threading.Thread(target=cleanup_old_files, daemon=True).start()

# ── Helpers ──────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are problematic in filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()

def download_mp3(url: str) -> Path | None:
    """
    Download audio from a YouTube URL as MP3 (best quality).
    Returns the path to the downloaded file, or None on failure.
    """
    # yt-dlp output template — sanitize to avoid shell issues
    outtmpl = str(DOWNLOAD_DIR / '%(title)s.%(ext)s')

    # Build the command — YT_DLP may be a path or a "python -m yt_dlp" string
    if " " in YT_DLP:
        base_cmd = YT_DLP.split()
    else:
        base_cmd = [YT_DLP]

    cmd = base_cmd + [
        "-x",                     # extract audio
        "--audio-format", "mp3",  # convert to mp3
        "--audio-quality", "0",   # best quality
        "--embed-thumbnail",      # embed cover art
        "--add-metadata",         # add metadata tags
        "--output", outtmpl,
        "--no-playlist",          # single video only
        url,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 min max per download
    )

    if result.returncode != 0:
        print(f"yt-dlp error: {result.stderr}")
        return None

    # After successful download, find the most recent MP3 file
    mp3s = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
    return mp3s[0] if mp3s else None

# ── Routes ──────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Introduce una URL de YouTube"}), 400

    # Basic validation
    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "URL no válida. Debe ser de YouTube."}), 400

    file_path = download_mp3(url)
    if not file_path or not file_path.exists():
        return jsonify({"error": "No se pudo descargar el audio. Revisa la URL."}), 500

    try:
        return send_file(
            str(file_path),
            as_attachment=True,
            mimetype="audio/mpeg",
            download_name=file_path.name,
        )
    except Exception as e:
        return jsonify({"error": f"Error al enviar el archivo: {str(e)}"}), 500


@app.route("/history")
def history():
    """Return list of recently downloaded files."""
    files = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
    items = []
    for f in files[:20]:
        size_mb = round(f.stat().st_size / (1024 * 1024), 2)
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
        items.append({"name": f.name, "size": size_mb, "date": mtime})
    return jsonify(items)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 dwyt corriendo en http://0.0.0.0:{port}")
    print(f"   Descargas → {DOWNLOAD_DIR}")
    app.run(host="0.0.0.0", port=port, debug=False)

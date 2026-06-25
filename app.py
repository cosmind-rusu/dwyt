#!/usr/bin/env python3
"""
dwyt — Download YouTube to MP3 web app.
"""

import base64
import os
import re
import shutil
import subprocess
import sys
import time
import threading
from pathlib import Path
from http.cookiejar import MozillaCookieJar
from flask import Flask, render_template, request, send_file, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

COOKIES_FILE = BASE_DIR / "cookies.txt"

# Find yt-dlp
YT_DLP = shutil.which("yt-dlp") or str(Path(sys.executable).parent / "yt-dlp")
if not Path(YT_DLP).exists():
    YT_DLP = f"{sys.executable} -m yt_dlp"

# ── Load cookies from env var on startup ────────────────────
_cookie_env = os.environ.get("YOUTUBE_COOKIES", "").strip()
if _cookie_env:
    try:
        decoded = base64.b64decode(_cookie_env).decode("utf-8")
        COOKIES_FILE.write_text(decoded)
        print(f"🍪 Cookies cargadas desde YOUTUBE_COOKIES ({len(decoded)} bytes)")
    except Exception as e:
        print(f"⚠️  Error al decodificar YOUTUBE_COOKIES: {e}")

# ── Periodic cleanup ──────────────────────────────────────────

MAX_FILE_AGE = 3600

def cleanup_old_files():
    while True:
        now = time.time()
        for f in DOWNLOAD_DIR.iterdir():
            if f.is_file() and f.name != "cookies.txt" and (now - f.stat().st_mtime) > MAX_FILE_AGE:
                f.unlink(missing_ok=True)
        time.sleep(300)

threading.Thread(target=cleanup_old_files, daemon=True).start()

# ── Cookie parsing ──────────────────────────────────────────

YOUTUBE_COOKIE_NAMES = {
    "SAPISID", "__Secure-3PSAPISID", "APISID", "SSID",
    "__Secure-3PAPISID", "SID", "HSID", "__Secure-3PSID",
    "LOGIN_INFO", "PREF", "YSC", "VISITOR_INFO1_LIVE",
}

def parse_cookies_file() -> dict:
    """Parse the cookies.txt and return diagnostic info."""
    result = {
        "exists": False,
        "size_bytes": 0,
        "count": 0,
        "domains": [],
        "youtube_cookies": [],
        "valid_format": False,
        "parse_error": None,
    }

    if not COOKIES_FILE.exists() or COOKIES_FILE.stat().st_size == 0:
        return result

    result["exists"] = True
    result["size_bytes"] = COOKIES_FILE.stat().st_size

    # Try parsing as Netscape format
    try:
        cj = MozillaCookieJar(str(COOKIES_FILE))
        cj.load(ignore_discard=True, ignore_expires=True)
        result["valid_format"] = True
        result["count"] = len(cj)

        domains = set()
        youtube_names = []
        for cookie in cj:
            domains.add(cookie.domain)
            if "youtube" in cookie.domain or "google" in cookie.domain or "ytimg" in cookie.domain:
                if cookie.name in YOUTUBE_COOKIE_NAMES:
                    youtube_names.append(cookie.name)

        result["domains"] = sorted(domains)
        result["youtube_cookies"] = sorted(set(youtube_names))
        result["has_auth_cookies"] = any(
            n in {"SAPISID", "__Secure-3PSAPISID", "SID", "__Secure-3PSID", "LOGIN_INFO"}
            for n in youtube_names
        )
    except Exception as e:
        result["parse_error"] = str(e)
        # Fallback: count lines starting with .
        lines = COOKIES_FILE.read_text().strip().split("\n")
        cookie_lines = [l for l in lines if l.strip() and not l.startswith("#")]
        result["count"] = len(cookie_lines)
        domains = set()
        for line in cookie_lines:
            parts = line.split("\t")
            if len(parts) >= 1 and parts[0].startswith("."):
                domains.add(parts[0])
        result["domains"] = sorted(domains) if domains else ["formato inválido"]

    return result

# ── Download helper ─────────────────────────────────────────

def download_mp3(url: str) -> Path:
    outtmpl = str(DOWNLOAD_DIR / '%(title)s.%(ext)s')

    if " " in YT_DLP:
        base_cmd = YT_DLP.split()
    else:
        base_cmd = [YT_DLP]

    cmd = base_cmd + [
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "--add-metadata",
        "--output", outtmpl,
        "--no-playlist",
        "--js-runtimes", "deno",
        "--remote-components", "ejs:github",
        "--extractor-retries", "5",
        "--retries", "10",
        "--verbose",  # verbose for debugging
    ]

    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        cmd += ["--cookies", str(COOKIES_FILE)]

    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        err_msg = result.stderr.strip() or "Unknown error"
        # Also log stdout for debugging
        print(f"yt-dlp STDOUT: {result.stdout[:2000]}")
        print(f"yt-dlp ERROR: {err_msg[:2000]}")
        raise RuntimeError(err_msg)

    mp3s = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
    if not mp3s:
        raise RuntimeError("No se generó ningún archivo MP3")
    return mp3s[0]

# ── Routes ──────────────────────────────────────────────────

@app.route("/")
def index():
    info = parse_cookies_file()
    return render_template("index.html", cookies_info=info)


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()
    if not url:
        return jsonify({"error": "Introduce una URL de YouTube"}), 400

    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "URL no válida. Debe ser de YouTube."}), 400

    try:
        file_path = download_mp3(url)
    except RuntimeError as e:
        return jsonify({"error": f"Error al descargar: {str(e)}"}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "La descarga tomó demasiado tiempo (>5 min)"}), 500
    except Exception as e:
        return jsonify({"error": f"Error inesperado: {str(e)}"}), 500

    try:
        return send_file(
            str(file_path),
            as_attachment=True,
            mimetype="audio/mpeg",
            download_name=file_path.name,
        )
    except Exception as e:
        return jsonify({"error": f"Error al enviar el archivo: {str(e)}"}), 500


@app.route("/cookies", methods=["GET", "POST"])
def cookies():
    if request.method == "GET":
        return jsonify(parse_cookies_file())

    data = request.get_data(as_text=True)
    if not data or len(data.strip()) < 10:
        return jsonify({"error": "Contenido de cookies demasiado corto"}), 400

    COOKIES_FILE.write_text(data.strip())
    print(f"🍪 Cookies guardadas ({len(data.strip())} bytes)")
    info = parse_cookies_file()
    return jsonify({"ok": True, **info})


@app.route("/history")
def history():
    files = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
    items = []
    for f in files[:20]:
        size_mb = round(f.stat().st_size / (1024 * 1024), 2)
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
        items.append({"name": f.name, "size": size_mb, "date": mtime})
    return jsonify(items)


@app.route("/health")
def health():
    checks = {}

    yt_path = shutil.which("yt-dlp")
    checks["yt-dlp"] = yt_path if yt_path else "NOT FOUND"
    if yt_path:
        try:
            ver = subprocess.run([yt_path, "--version"], capture_output=True, text=True, timeout=10)
            checks["yt-dlp_version"] = ver.stdout.strip() if ver.returncode == 0 else ver.stderr.strip()
        except Exception as e:
            checks["yt-dlp_error"] = str(e)

    ff_path = shutil.which("ffmpeg")
    checks["ffmpeg"] = ff_path if ff_path else "NOT FOUND"
    if ff_path:
        try:
            ver = subprocess.run([ff_path, "-version"], capture_output=True, text=True, timeout=10)
            checks["ffmpeg_version"] = ver.stdout.split("\n")[0] if ver.returncode == 0 else ver.stderr.strip()
        except Exception as e:
            checks["ffmpeg_error"] = str(e)

    deno_path = shutil.which("deno")
    checks["deno"] = deno_path if deno_path else "NOT FOUND"
    if deno_path:
        try:
            ver = subprocess.run([deno_path, "--version"], capture_output=True, text=True, timeout=10)
            checks["deno_version"] = ver.stdout.split("\n")[0] if ver.returncode == 0 else ver.stderr.strip()
        except Exception as e:
            checks["deno_error"] = str(e)

    checks["cookies"] = parse_cookies_file()

    try:
        statvfs = os.statvfs(str(DOWNLOAD_DIR))
        free_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
        checks["disk_free_mb"] = round(free_mb, 1)
    except Exception:
        checks["disk_free_mb"] = "unknown"

    checks["download_dir"] = str(DOWNLOAD_DIR)
    checks["download_dir_writable"] = os.access(str(DOWNLOAD_DIR), os.W_OK)

    return jsonify(checks)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cinfo = parse_cookies_file()
    print(f"🚀 dwyt corriendo en http://0.0.0.0:{port}")
    print(f"   Descargas → {DOWNLOAD_DIR}")
    if cinfo["exists"]:
        print(f"   Cookies → {cinfo['count']} cookies, {cinfo['size_bytes']} bytes")
        if cinfo.get("has_auth_cookies"):
            print(f"   Auth YouTube ✅")
        else:
            print(f"   Auth YouTube ❌ — pueden faltar cookies de autenticación")
    else:
        print(f"   Cookies → ❌ no configuradas")
    app.run(host="0.0.0.0", port=port, debug=False)

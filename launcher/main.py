from __future__ import annotations

import http.client
import os
import socket
import sys
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import tkinter as tk
from tkinter import messagebox

import uvicorn

HOST = "127.0.0.1"
API_PORT = 8000
WEB_PORT = 5173
APP_URL = f"http://{HOST}:{WEB_PORT}"
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


def resource_path(relative: str) -> Path:
    """Resolve files in source mode and in a PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, port))
            return True
        except OSError:
            return False


class LocalAppHandler(SimpleHTTPRequestHandler):
    """Serve the Vite build and proxy /api requests to the local FastAPI process."""

    def __init__(self, *args, directory: str, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args) -> None:
        # Keep the launcher window quiet; backend errors are shown in the app log.
        return

    def _is_backend_path(self) -> bool:
        path = urlsplit(self.path).path
        return path == "/api" or path.startswith("/api/") or path in {
            "/docs", "/openapi.json", "/redoc"
        }

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP and key.lower() != "host"
        }
        connection = http.client.HTTPConnection(HOST, API_PORT, timeout=600)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP_BY_HOP:
                    self.send_header(key, value)
            self.end_headers()
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except Exception:
            self.send_error(502, "Backend lokal tidak dapat dihubungi.")
        finally:
            connection.close()

    def _serve_frontend(self) -> None:
        requested = urlsplit(self.path).path
        local_path = Path(self.translate_path(requested))
        # React Router paths should load the SPA entry point.
        if not local_path.is_file() and not requested.startswith("/assets/"):
            self.path = "/index.html"
        super().do_GET()

    def do_GET(self) -> None:
        if self._is_backend_path():
            self._proxy()
        else:
            self._serve_frontend()

    def do_HEAD(self) -> None:
        if self._is_backend_path():
            self._proxy()
        else:
            requested = urlsplit(self.path).path
            local_path = Path(self.translate_path(requested))
            if not local_path.is_file() and not requested.startswith("/assets/"):
                self.path = "/index.html"
            super().do_HEAD()

    def do_POST(self) -> None:
        self._proxy() if self._is_backend_path() else self.send_error(405)

    def do_PUT(self) -> None:
        self._proxy() if self._is_backend_path() else self.send_error(405)

    def do_PATCH(self) -> None:
        self._proxy() if self._is_backend_path() else self.send_error(405)

    def do_DELETE(self) -> None:
        self._proxy() if self._is_backend_path() else self.send_error(405)

    def do_OPTIONS(self) -> None:
        self._proxy() if self._is_backend_path() else self.send_error(405)


class Launcher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FSS Control Center")
        self.root.geometry("430x190")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

        self.status = tk.StringVar(value="Menyiapkan FSS Control Center...")
        tk.Label(root, text="FSS CONTROL CENTER", font=("Segoe UI", 15, "bold")).pack(pady=(16, 4))
        tk.Label(root, textvariable=self.status, font=("Segoe UI", 10), wraplength=390).pack(pady=8)

        buttons = tk.Frame(root)
        buttons.pack(pady=10)
        self.open_button = tk.Button(
            buttons, text="Buka Aplikasi", width=16, state=tk.DISABLED,
            command=lambda: webbrowser.open(APP_URL)
        )
        self.open_button.pack(side=tk.LEFT, padx=5)
        tk.Button(buttons, text="Tutup", width=12, command=self.stop).pack(side=tk.LEFT, padx=5)

        self.api_server = None
        self.api_thread = None
        self.web_server = None
        self.web_thread = None
        self.opened = False
        self.started_at = time.monotonic()

        self._start_services()
        self.root.after(300, self._check_ready)

    def _start_services(self) -> None:
        frontend_dist = resource_path("fe/dist")
        backend_root = resource_path("be")

        if not (frontend_dist / "index.html").is_file():
            messagebox.showerror(
                "Frontend belum dibangun",
                "Folder fe/dist/index.html tidak ditemukan.\n"
                "Jalankan launcher/build_windows.bat untuk membangun aplikasi."
            )
            self.root.after(0, self.stop)
            return

        if not port_is_free(API_PORT) or not port_is_free(WEB_PORT):
            messagebox.showerror(
                "Port sedang digunakan",
                "Port 8000 atau 5173 sedang digunakan.\n"
                "Tutup instance FSS Control Center yang lama, lalu jalankan kembali."
            )
            self.root.after(0, self.stop)
            return

        # Keep SQLite settings/history in the user's Windows profile, not beside the EXE.
        data_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        data_dir = data_dir / "FSSControlCenter" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["FSS_DATA_DIR"] = str(data_dir)

        sys.path.insert(0, str(backend_root))
        try:
            from app.main import app
        except Exception as exc:
            messagebox.showerror(
                "Backend gagal dimuat",
                f"Backend tidak dapat dimulai:\n{exc}"
            )
            self.root.after(0, self.stop)
            return

        config = uvicorn.Config(
            app,
            host=HOST,
            port=API_PORT,
            log_level="warning",
            access_log=False,
            reload=False,
        )
        self.api_server = uvicorn.Server(config)
        self.api_thread = threading.Thread(target=self.api_server.run, daemon=True)
        self.api_thread.start()

        handler = partial(LocalAppHandler, directory=str(frontend_dist))
        try:
            self.web_server = ThreadingHTTPServer((HOST, WEB_PORT), handler)
        except OSError as exc:
            messagebox.showerror("Web server gagal", f"Tidak dapat membuka port {WEB_PORT}:\n{exc}")
            self.root.after(0, self.stop)
            return

        self.web_thread = threading.Thread(target=self.web_server.serve_forever, daemon=True)
        self.web_thread.start()

    def _check_ready(self) -> None:
        if self.api_server is None:
            return
        if self.api_server.started and self.web_thread and self.web_thread.is_alive():
            self.status.set("Backend aktif. Aplikasi siap digunakan di laptop ini.")
            self.open_button.config(state=tk.NORMAL)
            if not self.opened:
                self.opened = True
                webbrowser.open(APP_URL)
            return

        if time.monotonic() - self.started_at > 30:
            self.status.set("Backend belum berhasil aktif. Tutup aplikasi dan periksa instalasi.")
            return

        self.root.after(300, self._check_ready)

    def stop(self) -> None:
        if self.api_server is not None:
            self.api_server.should_exit = True
        if self.web_server is not None:
            try:
                self.web_server.shutdown()
                self.web_server.server_close()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    Launcher(window)
    window.mainloop()

"""Servidor local del juego: sirve los archivos y guarda los mundos de cada jugador en partidas/<jugador>/<mundo>.json."""
import json
import os
import re
import shutil
import sys
import threading
import urllib.parse
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

RAIZ = os.path.dirname(os.path.abspath(__file__))
PARTIDAS = os.path.join(RAIZ, "partidas")
PUERTO = 8766
MAX_BYTES = 30 * 1024 * 1024


def limpio(nombre):
    """Nombre seguro para carpeta o archivo: letras (con tildes), números, espacio, guion y guion bajo."""
    return re.sub(r"[^\w\- ]", "", (nombre or "").strip())[:40].strip()


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RAIZ, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass

    def responder(self, codigo, obj):
        datos = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def ruta(self):
        u = urllib.parse.urlparse(self.path)
        return u.path, dict(urllib.parse.parse_qsl(u.query))

    def do_GET(self):
        ruta, q = self.ruta()
        if ruta == "/api/ping":
            return self.responder(200, {"ok": True, "carpeta": PARTIDAS})
        if ruta == "/api/jugadores":
            os.makedirs(PARTIDAS, exist_ok=True)
            return self.responder(200, sorted(d for d in os.listdir(PARTIDAS) if os.path.isdir(os.path.join(PARTIDAS, d))))
        if ruta == "/api/mundos":
            carpeta = os.path.join(PARTIDAS, limpio(q.get("jugador")))
            lista = []
            if limpio(q.get("jugador")) and os.path.isdir(carpeta):
                for f in os.listdir(carpeta):
                    if not f.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(carpeta, f), encoding="utf-8") as fh:
                            d = json.load(fh)
                        lista.append({"id": f[:-5], "nombre": d.get("nombre", f[:-5]), "tipo": d.get("tipo", "normal"),
                                      "jugado": d.get("jugado", "")})
                    except (OSError, ValueError):
                        pass
            lista.sort(key=lambda m: m["jugado"], reverse=True)
            return self.responder(200, lista)
        if ruta == "/api/mundo":
            j, m = limpio(q.get("jugador")), limpio(q.get("mundo"))
            archivo = os.path.join(PARTIDAS, j, m + ".json")
            if not (j and m and os.path.isfile(archivo)):
                return self.responder(404, {"error": "no existe"})
            with open(archivo, encoding="utf-8") as fh:
                return self.responder(200, json.load(fh))
        return super().do_GET()

    def do_POST(self):
        ruta, q = self.ruta()
        if ruta == "/api/jugador":
            j = limpio(q.get("nombre"))
            if not j:
                return self.responder(400, {"error": "nombre vacío"})
            os.makedirs(os.path.join(PARTIDAS, j), exist_ok=True)
            return self.responder(200, {"ok": True, "jugador": j})
        if ruta == "/api/mundo":
            j, m = limpio(q.get("jugador")), limpio(q.get("mundo"))
            largo = int(self.headers.get("Content-Length") or 0)
            if not (j and m) or largo <= 0 or largo > MAX_BYTES:
                return self.responder(400, {"error": "datos inválidos"})
            try:
                datos = json.loads(self.rfile.read(largo).decode("utf-8"))
            except ValueError:
                return self.responder(400, {"error": "JSON inválido"})
            carpeta = os.path.join(PARTIDAS, j)
            os.makedirs(carpeta, exist_ok=True)
            archivo = os.path.join(carpeta, m + ".json")
            temporal = archivo + ".tmp"
            with open(temporal, "w", encoding="utf-8") as fh:
                json.dump(datos, fh, ensure_ascii=False)
            if os.path.isfile(archivo):
                shutil.copyfile(archivo, archivo + ".bak")      # copia de la versión anterior, por si acaso
            os.replace(temporal, archivo)
            return self.responder(200, {"ok": True, "archivo": archivo})
        return self.responder(404, {"error": "ruta desconocida"})


if __name__ == "__main__":
    os.makedirs(PARTIDAS, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    url = f"http://localhost:{PUERTO}/juego.html"
    print(f"Juego en {url}  (no cierres esta ventana mientras juegas)")
    print(f"Partidas en {PARTIDAS}")
    if "--sin-navegador" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    servidor.serve_forever()

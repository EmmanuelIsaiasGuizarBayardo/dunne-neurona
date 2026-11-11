"""Prueba de punta a punta del servidor de la sala.

Emplea la biblioteca `websockets` como cliente para que la implementación
del protocolo se valide contra una independiente y no contra sí misma.
"""
import asyncio, json, threading, time, sys
from pathlib import Path
import websockets

# El directorio del archivo, no el de trabajo: la suite debe poder ejecutarse
# desde la raíz del repositorio (`python sala/test_sala.py`) además de desde
# esta carpeta.
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from server import serve

PORT = 8399
srv = serve("127.0.0.1", PORT, ROOT, {"topology": "cadena", "dilation": 1})
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.4)
URL = f"ws://127.0.0.1:{PORT}/ws"

fails = []
def check(label, ok, detail=""):
    print(f"  {'OK  ' if ok else 'FALLA'} {label}{'  ' + str(detail) if detail else ''}")
    if not ok: fails.append(label)

async def recv_until(ws, kind, pred, timeout=4.0):
    """Espera un mensaje del tipo dado que además cumpla una condición.

    Una neurona recibe un mensaje `targets` por cada cambio del censo, por lo
    que hay que filtrar hasta el que refleja el estado buscado.
    """
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        msg = await recv(ws, kind, end - time.monotonic())
        last = msg
        if pred(msg):
            return msg
    raise TimeoutError(f"{kind} con la condición pedida; último: {last}")


async def recv(ws, kind, timeout=4.0):
    """Espera el primer mensaje de un tipo dado."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        raw = await asyncio.wait_for(ws.recv(), timeout=end - time.monotonic())
        msg = json.loads(raw)
        if msg.get("type") == kind:
            return msg
    raise TimeoutError(kind)

async def main():
    # --- tres neuronas y un mural ---
    async with websockets.connect(URL) as a, websockets.connect(URL) as b, \
               websockets.connect(URL) as c, \
               websockets.connect(URL + "?role=mural") as mural:

        wa = await recv(a, "welcome"); wb = await recv(b, "welcome"); wc = await recv(c, "welcome")
        wm = await recv(mural, "welcome")

        check("asientos consecutivos", [wa["seat"], wb["seat"], wc["seat"]] == [1,2,3],
              [wa["seat"], wb["seat"], wc["seat"]])
        check("el mural no ocupa asiento", wm["seat"] is None)
        # El welcome de la primera se emite cuando aún está sola; los
        # destinos definitivos llegan en el mensaje "targets".
        upd = await recv_until(a, "targets", lambda m: m["targets"] == [2])
        check("cadena: 1 aprende que apunta a 2", upd["targets"] == [2], upd["targets"])
        check("cadena: el último no apunta a nadie", wc["targets"] == [], wc["targets"])

        roster = await recv(mural, "roster")
        check("censo con 3 neuronas", len(roster["neurons"]) == 3, len(roster["neurons"]))
        check("aristas de la cadena", roster["edges"] == [[1,2],[2,3]], roster["edges"])

        # --- un spike de 1 llega a 2 y no a 3 ---
        await a.send(json.dumps({"type": "spike"}))
        got = await recv(b, "input")
        check("el spike llega a la postsináptica", got["from_seat"] == 1, got)
        check("trae peso sináptico", got["weight"] == 0.6, got["weight"])
        check("el mural registra el evento", (await recv(mural, "event"))["seat"] == 1)
        try:
            await asyncio.wait_for(recv(c, "input", 0.8), timeout=1.0)
            check("no llega a quien no es postsináptica", False)
        except (TimeoutError, asyncio.TimeoutError):
            check("no llega a quien no es postsináptica", True)

        # --- desmielinización: el retardo se dispara ---
        d_mielin = got["delay_ms"]
        await a.send(json.dumps({"type": "myelin", "on": False}))
        await recv(mural, "roster")
        await a.send(json.dumps({"type": "spike"}))
        got2 = await recv(b, "input", 8.0)
        check("sin mielina el retardo crece ×10",
              abs(got2["delay_ms"] / d_mielin - 10) < 0.05,
              f"{d_mielin:.1f} ms → {got2['delay_ms']:.1f} ms")

        # --- cambio de topología desde el mural ---
        await mural.send(json.dumps({"type": "config", "topology": "convergencia"}))
        wa2 = await recv(a, "welcome")
        wc2 = await recv(c, "welcome")
        check("convergencia: 1 apunta a la última", wa2["targets"] == [3], wa2["targets"])
        check("convergencia: la última no tiene salida", wc2["targets"] == [], wc2["targets"])

        # --- suma espacial: 1 y 2 llegan ambas a 3 ---
        await a.send(json.dumps({"type": "spike"}))
        await b.send(json.dumps({"type": "spike"}))
        i1 = await recv(c, "input", 8.0); i2 = await recv(c, "input", 8.0)
        check("dos entradas convergen en la misma neurona",
              {i1["from_seat"], i2["from_seat"]} == {1, 2}, (i1["from_seat"], i2["from_seat"]))

    # --- mural: censo, voltaje en vivo y consola del operador ---
    async with websockets.connect(URL) as a, websockets.connect(URL) as b, \
               websockets.connect(URL + "?role=mural") as mural:
        await recv(a, "welcome"); await recv(b, "welcome"); await recv(mural, "welcome")
        r = await recv(mural, "roster")
        check("el censo trae polaridad, mielina y voltaje",
              all(k in r["neurons"][0] for k in ("polarity", "myelinated", "vm")))

        await a.send(json.dumps({"type": "vm", "v": -61.5}))
        v = await recv(mural, "vm")
        check("el voltaje llega al mural", v["seat"] == 1 and v["v"] == -61.5, v)
        try:
            await asyncio.wait_for(recv(b, "vm", 0.7), timeout=0.9)
            check("el voltaje NO se difunde a las neuronas", False)
        except (TimeoutError, asyncio.TimeoutError):
            check("el voltaje NO se difunde a las neuronas", True)

        await mural.send(json.dumps({"type": "config", "topology": "anillo", "dilation": 30}))
        r2 = await recv(mural, "roster")
        check("la consola cambia topología y dilatación",
              r2["config"]["topology"] == "anillo" and r2["config"]["dilation"] == 30)
        check("el anillo cierra el circuito", sorted(r2["edges"]) == [[1, 2], [2, 1]], r2["edges"])

        await mural.send(json.dumps({"type": "polarity", "seat": 2, "kind": "inhibitory"}))
        check("la consola invierte la polaridad de un asiento",
              (await recv(b, "polarity"))["kind"] == "inhibitory")

        await mural.send(json.dumps({"type": "reset"}))
        check("el reset llega a las neuronas", (await recv(a, "reset"))["type"] == "reset")

        await a.send(json.dumps({"type": "spike"}))
        e = await recv(mural, "event")
        check("el evento trae lo que el grafo necesita",
              all(k in e for k in ("seat", "targets", "delay_ms", "polarity")))

    # --- circuitos independientes, control del operador y bloqueo ---
    async with websockets.connect(URL) as a, websockets.connect(URL) as b, \
               websockets.connect(URL) as c, websockets.connect(URL) as d, \
               websockets.connect(URL + "?role=mural") as mural:
        for ws in (a, b, c, d, mural):
            await recv(ws, "welcome")

        await mural.send(json.dumps({"type": "config", "topology": "cadena", "groups": 2}))
        r = await recv_until(mural, "roster",
                             lambda m: m["config"]["groups"] == 2
                             and m["config"]["topology"] == "cadena", 6.0)
        grupos = {n["seat"]: n["group"] for n in r["neurons"]}
        check("cuatro asientos repartidos en dos circuitos",
              grupos == {1: 1, 2: 1, 3: 2, 4: 2}, grupos)
        check("las aristas no cruzan de circuito",
              sorted(r["edges"]) == [[1, 2], [3, 4]], r["edges"])

        # Un spike del asiento 2 no puede alcanzar al 3: están en circuitos
        # distintos aunque sean asientos consecutivos.
        await b.send(json.dumps({"type": "spike"}))
        try:
            await asyncio.wait_for(recv(c, "input", 1.0), timeout=1.2)
            check("la señal no cruza entre circuitos", False)
        except (TimeoutError, asyncio.TimeoutError):
            check("la señal no cruza entre circuitos", True)

        # El operador cambia la mielina de un asiento concreto.
        await mural.send(json.dumps({"type": "myelin", "on": False, "seat": 1}))
        m = await recv(a, "myelin", 4.0)
        check("el operador apaga la mielina de un asiento", m["on"] is False, m)

        # Con el bloqueo puesto, la neurona ya no puede cambiarse a sí misma.
        await mural.send(json.dumps({"type": "config", "locked": True}))
        await recv_until(mural, "roster", lambda m: m["config"]["locked"], 6.0)
        await a.send(json.dumps({"type": "polarity", "kind": "inhibitory"}))
        blocked = await recv(a, "locked", 4.0)
        check("el bloqueo impide que la neurona cambie su tipo",
              blocked["reason"] == "polarity", blocked)

        # Pero el operador sí puede, incluso con el bloqueo puesto.
        await mural.send(json.dumps({"type": "polarity", "kind": "inhibitory", "seat": 1}))
        p = await recv(a, "polarity", 4.0)
        check("el operador sí puede con el bloqueo puesto", p["kind"] == "inhibitory", p)

        await mural.send(json.dumps({"type": "config", "locked": False, "groups": 1}))
        r2 = await recv_until(mural, "roster",
                              lambda m: m["config"]["groups"] == 1
                              and not m["config"]["locked"], 6.0)
        check("volver a un circuito reconecta la cadena",
              sorted(r2["edges"]) == [[1, 2], [2, 3], [3, 4]], r2["edges"])

    # --- juegos colaborativos ---
    async with websockets.connect(URL) as a, websockets.connect(URL) as b, \
               websockets.connect(URL) as c, websockets.connect(URL) as d, \
               websockets.connect(URL + "?role=mural") as mural:
        for ws in (a, b, c, d, mural):
            await recv(ws, "welcome")

        # El toque llega al mural aunque no haya juego, y no a las neuronas.
        await a.send(json.dumps({"type": "tap"}))
        t = await recv(mural, "tap", 4.0)
        check("el toque llega al mural para construir la onda", t["seat"] == 1, t)
        try:
            await asyncio.wait_for(recv(b, "tap", 0.6), timeout=0.8)
            check("el toque NO se difunde a las neuronas", False)
        except (TimeoutError, asyncio.TimeoutError):
            check("el toque NO se difunde a las neuronas", True)

        # Sincronía: con cuatro neuronas y quórum de 0.5 hacen falta dos.
        await mural.send(json.dumps({"type": "game", "action": "start", "kind": "sync"}))
        st = await recv_until(mural, "game", lambda m: m.get("state"), 4.0)
        check("la sincronía exige un quórum", st["state"]["quorum"] == 2, st["state"])

        await a.send(json.dumps({"type": "tap"}))
        st = await recv_until(mural, "game",
                              lambda m: (m.get("state") or {}).get("in_window") == 1, 4.0)
        check("un toque solo no dispara", st["state"]["hits"] == 0, st["state"])

        await b.send(json.dumps({"type": "tap"}))
        fire = await recv_until(mural, "game", lambda m: m.get("event") == "fire", 4.0)
        check("dos toques coincidentes disparan la neurona compartida", fire["kind"] == "sync")

        # Fuera de la ventana no hay coincidencia.
        await asyncio.sleep(1.2)
        await c.send(json.dumps({"type": "tap"}))
        await asyncio.sleep(0.7)
        await d.send(json.dumps({"type": "tap"}))
        st = await recv_until(mural, "game",
                              lambda m: (m.get("state") or {}).get("in_window") == 1, 4.0)
        check("toques espaciados no se suman", st["state"]["hits"] == 1, st["state"])

        await mural.send(json.dumps({"type": "game", "action": "stop"}))
        await recv_until(mural, "game", lambda m: m.get("state") is None, 4.0)

        # Tirón: dos excitatorias contra dos inhibitorias.
        await mural.send(json.dumps({"type": "game", "action": "start", "kind": "tug",
                                     "duration_s": 30, "step_mv": 3.0, "max_rate_hz": 3}))
        r = await recv_until(mural, "roster", lambda m: m["config"]["locked"], 4.0)
        equipos = {n["seat"]: n["polarity"] for n in r["neurons"]}
        check("el tirón forma dos equipos y bloquea los tipos",
              equipos == {1: "excitatory", 2: "excitatory", 3: "inhibitory", 4: "inhibitory"},
              equipos)

        # El tope por persona: diez toques seguidos de una sola neurona solo
        # cuentan tres en un segundo.
        for _ in range(10):
            await a.send(json.dumps({"type": "tap"}))
        await asyncio.sleep(0.25)
        st = await recv_until(mural, "game",
                              lambda m: (m.get("state") or {}).get("count", {}).get("excitatory", 0) >= 3,
                              4.0)
        check("el tope impide que una sola persona domine",
              st["state"]["count"]["excitatory"] == 3, st["state"]["count"])

        # Dos personas participando superan a una sola insistiendo.
        for _ in range(3):
            await b.send(json.dumps({"type": "tap"}))
        fire = await recv_until(mural, "game", lambda m: m.get("event") == "fire", 4.0)
        check("la excitación coordinada alcanza el umbral", fire["winner"] == "excitatory")

        await mural.send(json.dumps({"type": "game", "action": "stop"}))
        r = await recv_until(mural, "roster", lambda m: not m["config"]["locked"], 4.0)
        check("detener el juego libera el bloqueo", not r["config"]["locked"])

        # Tirón con tiempo agotado: gana la inhibición.
        await mural.send(json.dumps({"type": "game", "action": "start", "kind": "tug",
                                     "duration_s": 0.6}))
        end = await recv_until(mural, "game", lambda m: m.get("event") == "end", 4.0)
        check("si el tiempo se agota sin disparo, gana la inhibición",
              end["winner"] == "inhibitory")
        await mural.send(json.dumps({"type": "game", "action": "stop"}))

    # --- al salir todos, el censo queda vacío ---
    await asyncio.sleep(0.3)
    check("los clientes se dieron de baja", len(srv.hub.clients) == 0, len(srv.hub.clients))

    # --- el mismo puerto sirve archivos estáticos ---
    # Se solicita un archivo existente en lugar de crear uno temporal: en
    # Windows no se puede eliminar un archivo que el hilo del servidor
    # mantiene abierto.
    import urllib.request
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/sala.css") as r:
        body = r.read().decode("utf-8")
        check("HTTP y WebSocket en el mismo puerto",
              r.status == 200 and "--flame" in body, f"{r.status}, {len(body)} bytes")
        check("respuestas sin caché", r.headers.get("Cache-Control") == "no-store")

    # --- las rutas cortas del QR resuelven al cliente ---
    for short, marker in (("/n", "Tu neurona"), ("/", "Tu neurona")):
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{short}") as r:
            check(f"ruta corta {short}", r.status == 200 and marker in r.read().decode("utf-8"))

asyncio.run(main())
print()
print("PRUEBA FALLIDA:" if fails else "TODAS LAS VERIFICACIONES PASAN")
for f in fails: print("  -", f)
sys.exit(1 if fails else 0)

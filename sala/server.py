#!/usr/bin/env python3
"""Servidor de la sala interactiva de DUNNE.

Cada dispositivo conectado es una neurona. El servidor mantiene la topología
del circuito, recibe los potenciales de acción que dispara cada uno y los
entrega a sus neuronas postsinápticas con un retardo de conducción calculado.

Decisiones de diseño y por qué
------------------------------
**Un solo puerto para HTTP y WebSocket.** Un navegador en una página servida
por HTTPS no puede abrir un WebSocket ``ws://``: lo bloquea como contenido
mixto activo. Sirviendo la página y el socket desde el mismo origen en HTTP
el problema no existe, y en la sala no hace falta HTTPS porque no se usa la
cámara. Esto permite que un celular del público entre escaneando un QR sin
instalar ni configurar nada.

**Sin dependencias.** El protocolo WebSocket está implementado sobre la
biblioteca estándar, de modo que el despliegue no depende de que un
``pip install`` funcione en el equipo de la sede.

**Mensajes JSON planos.** Compatibles con ``WebSocketsClient`` de ESP32 y
puenteables a MQTT sin modificar el protocolo.

Protocolo
---------
Cliente al servidor:
    ``{"type": "hello", "role": "neuron"|"mural", "seat": int|null}``
    ``{"type": "spike", "at": <ms del cliente>}``
    ``{"type": "vm", "v": <mV>}``            (opcional, para el mural)
    ``{"type": "config", ...}``              (solo desde el mural)
    ``{"type": "myelin", "on": bool}``

Servidor al cliente:
    ``{"type": "welcome", "id":…, "seat":…, "config":…, "targets":…}``
    ``{"type": "input", "from_seat":…, "weight":…}``
    ``{"type": "roster", "neurons": […], "config":…}``
    ``{"type": "event", "kind": "spike", "seat":…, "t":…}``   (al mural)

Ejemplo
-------
$ python server.py --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import deque
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Parámetros del circuito
# ---------------------------------------------------------------------------

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

DEFAULT_CONFIG: dict[str, Any] = {
    # Dilatación temporal. A escala real el potencial de acción recorre la
    # sala en menos de un milisegundo. Con factor 20, la constante de membrana
    # de 20 ms equivale a 400 ms de reloj de pared, rango en el que la suma
    # temporal es reproducible con la mano. Los clientes muestran el factor en
    # pantalla para no representar una velocidad falsa.
    "dilation": 20,

    # Conducción. Longitud típica de un axón motor y velocidades del orden de
    # las fibras mielinizadas gruesas frente a las delgadas. La razón de 10
    # entre ambas está comprimida respecto a la real, que puede superar 20,
    # para acotar la duración de la demostración de desmielinización.
    "axon_length_m": 0.8,
    "v_myelinated_ms": 60.0,
    "v_unmyelinated_ms": 6.0,

    # Peso sináptico como fracción de la distancia entre reposo y umbral.
    # Con 0.6 se requieren dos entradas coincidentes para alcanzar el umbral.
    "weight": 0.6,

    # Topología inicial. La orgánica no tiene la regularidad de una cadena:
    # conexiones mayormente locales, con atajos ocasionales, bucles y
    # neuronas que reciben de varias a la vez.
    "topology": "organica",

    # Tamaño de grupo para convergencia y divergencia: cuántas neuronas
    # convergen sobre una, o sobre cuántas diverge una.
    "fan": 3,

    # Semilla de la topología orgánica. La misma semilla produce la misma red.
    "seed": 7,

    # Número de circuitos independientes. Con 2, los asientos se reparten en
    # dos mitades que no se conectan entre sí, lo que permite comparar dos
    # condiciones en paralelo o enfrentarlas.
    "groups": 1,

    # Con el bloqueo activo, las neuronas no pueden cambiar su propio tipo:
    # solo el operador desde el mural. Necesario cuando la configuración del
    # circuito es parte de la demostración.
    "locked": False,
}

TOPOLOGIES = ("organica", "cadena", "anillo", "convergencia", "divergencia")
MAX_FAN = 39

# Juegos colaborativos. Ambos convierten a todo el grupo en las entradas de
# una sola neurona compartida, de modo que el resultado depende del grupo y
# no de una persona.
GAME_DEFAULTS: dict[str, dict[str, float]] = {
    # Detección de coincidencias: la neurona compartida dispara solo si una
    # fracción del grupo toca dentro de la misma ventana breve. No se gana con
    # velocidad sino con coordinación.
    "sync": {"window_ms": 500.0, "quorum": 0.5, "refractory_ms": 900.0},

    # Suma de excitación contra inhibición. El tope de toques por persona
    # hace que gane el equipo donde más gente participa, no donde alguien
    # teclea más rápido; sin él el juego favorece a quien tiene más agilidad.
    "tug": {"step_mv": 0.9, "tau_ms": 1800.0, "duration_s": 20.0,
            "max_rate_hz": 3.0},
}
V_REST, V_THRESHOLD, V_FLOOR = -70.0, -55.0, -85.0


# ---------------------------------------------------------------------------
# WebSocket sobre biblioteca estándar
# ---------------------------------------------------------------------------

def accept_key(client_key: str) -> str:
    """Calcula el valor de ``Sec-WebSocket-Accept`` del handshake.

    Parameters
    ----------
    client_key : str
        Valor de ``Sec-WebSocket-Key`` enviado por el cliente.

    Returns
    -------
    str
        Hash SHA-1 del key concatenado con el GUID del protocolo, en base64.
    """
    digest = hashlib.sha1((client_key + WS_MAGIC).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(payload: bytes, opcode: int = OP_TEXT) -> bytes:
    """Arma un frame de servidor, que por especificación va sin máscara."""
    head = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        head += bytes([length])
    elif length < 65536:
        head += bytes([126]) + struct.pack(">H", length)
    else:
        head += bytes([127]) + struct.pack(">Q", length)
    return head + payload


def read_exactly(reader: Any, count: int) -> bytes:
    """Lee exactamente ``count`` bytes de un flujo o levanta ``ConnectionError``.

    Opera sobre el ``rfile`` del manejador y no sobre el socket crudo: el
    handshake se leyó con ese búfer, y los frames que el cliente haya enviado
    pegados a la petición ya están ahí. Leer del socket los descartaría.
    """
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = reader.read(remaining)
        if not chunk:
            raise ConnectionError("el par cerró la conexión")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(sock: Any) -> tuple[int, bytes]:
    """Lee un frame y devuelve ``(opcode, payload)``.

    Notes
    -----
    No se maneja fragmentación. Los mensajes son objetos JSON de pocos
    cientos de bytes, por debajo del umbral de fragmentación de cualquier
    navegador. Un frame de continuación se trataría como mensaje propio y se
    descartaría al fallar el parseo de JSON.
    """
    first, second = read_exactly(sock, 2)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F

    if length == 126:
        length = struct.unpack(">H", read_exactly(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read_exactly(sock, 8))[0]

    mask = read_exactly(sock, 4) if masked else b""
    payload = read_exactly(sock, length) if length else b""

    if masked:
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))

    return opcode, payload


# ---------------------------------------------------------------------------
# Clientes y concentrador
# ---------------------------------------------------------------------------

@dataclass
class Client:
    """Una conexión WebSocket viva.

    Attributes
    ----------
    sock : socket.socket
        Socket ya promovido a WebSocket.
    cid : int
        Identificador interno, único por conexión.
    role : str
        ``"neuron"`` para un dispositivo que es una neurona, ``"mural"`` para
        una pantalla de monitoreo.
    seat : int or None
        Posición en el circuito. Solo las neuronas tienen asiento.
    """

    sock: socket.socket
    cid: int
    role: str = "neuron"
    seat: int | None = None
    myelinated: bool = True
    # Polaridad de la neurona, no de la sinapsis. Por el principio de Dale,
    # una neurona libera el mismo neurotransmisor en todos sus terminales, de
    # modo que su efecto es excitatorio o inhibitorio, nunca mixto.
    polarity: str = "excitatory"
    group: int = 1
    last_vm: float = -70.0
    alive: bool = True
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def send(self, message: dict[str, Any]) -> bool:
        """Envía un mensaje JSON. Devuelve ``False`` si la conexión murió.

        El candado por cliente es necesario porque los envíos llegan desde
        hilos distintos: el hilo de la conexión que originó el spike y los
        temporizadores de entrega.
        """
        if not self.alive:
            return False
        data = encode_frame(json.dumps(message, ensure_ascii=False).encode("utf-8"))
        try:
            with self._lock:
                self.sock.sendall(data)
            return True
        except OSError:
            self.alive = False
            return False


class Hub:
    """Estado compartido de la sala: clientes, topología y configuración."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.clients: dict[int, Client] = {}
        self.config: dict[str, Any] = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self._next_cid = 1
        self._lock = threading.RLock()
        self.game: dict[str, Any] | None = None

        # Conexiones explícitas, como pares (origen, destino). Las topologías
        # predefinidas las generan; en modo manual el operador las edita y la
        # lista queda congelada aunque entren o salgan neuronas.
        self.edges: set[tuple[int, int]] = set()
        self.manual = False
        self.log: Callable[[str], None] = print

    # -- ciclo de vida ----------------------------------------------------

    def join(self, sock: socket.socket, role: str, seat: int | None) -> Client:
        """Registra una conexión y le asigna asiento si es una neurona."""
        with self._lock:
            cid = self._next_cid
            self._next_cid += 1
            client = Client(sock=sock, cid=cid, role=role)

            if role == "neuron":
                taken = {c.seat for c in self.clients.values() if c.seat is not None}
                if seat is not None and seat not in taken:
                    client.seat = seat
                else:
                    # Se reutiliza el primer asiento libre para no dejar
                    # huecos en la cadena tras una desconexión.
                    candidate = 1
                    while candidate in taken:
                        candidate += 1
                    client.seat = candidate

            self.clients[cid] = client

        self.regroup()
        self.rebuild_edges()
        client.send({
            "type": "welcome",
            "id": cid,
            "seat": client.seat,
            "role": role,
            "polarity": client.polarity,
            "group": client.group,
            "config": self.config,
            "targets": self.targets_of(client.seat) if client.seat else [],
        })
        self.broadcast_roster()
        self.log(f"entra {role} cid={cid} asiento={client.seat}")
        return client

    def leave(self, client: Client) -> None:
        """Retira una conexión y avisa al resto."""
        with self._lock:
            client.alive = False
            self.clients.pop(client.cid, None)
        self.regroup()
        self.rebuild_edges()
        self.broadcast_roster()
        self.log(f"sale {client.role} cid={client.cid} asiento={client.seat}")

    # -- topología --------------------------------------------------------

    def regroup(self) -> None:
        """Reparte los asientos entre los circuitos configurados.

        Los asientos ordenados se parten en mitades contiguas, de modo que
        cada circuito quede con una secuencia continua y la topología se
        aplique dentro de cada uno por separado.
        """
        order = self.seats()
        wanted = max(1, int(self.config.get("groups", 1)))
        half = (len(order) + 1) // 2
        with self._lock:
            for client in self.clients.values():
                if client.seat is None:
                    continue
                if wanted <= 1:
                    client.group = 1
                else:
                    client.group = 1 if order.index(client.seat) < half else 2

    def group_of(self, seat: int) -> int:
        """Circuito al que pertenece un asiento."""
        client = self.by_seat(seat)
        return client.group if client else 1

    def seats(self) -> list[int]:
        """Asientos ocupados, en orden."""
        with self._lock:
            return sorted(c.seat for c in self.clients.values() if c.seat is not None)

    def targets_of(self, seat: int | None) -> list[int]:
        """Asientos postsinápticos de un asiento dado.

        Se leen de la lista explícita de conexiones. Se descartan destinos
        ausentes y, con dos circuitos, los que pertenecen al otro circuito,
        de modo que ninguna conexión manual pueda romper su independencia.
        """
        if seat is None:
            return []
        present = set(self.seats())
        mine = self.group_of(seat)
        return sorted(b for a, b in self.edges
                      if a == seat and b in present and self.group_of(b) == mine)

    # -- generación de topologías -----------------------------------------

    @staticmethod
    def _uniform(seed: int, a: int, b: int) -> float:
        """Número en [0, 1) determinista para el par ordenado (a, b).

        Se usa un hash y no un generador aleatorio con estado: así la
        existencia de la conexión a→b depende solo de a, b y la semilla, y no
        del orden en que llegaron las neuronas ni de cuántas hay.
        """
        digest = hashlib.blake2b(f"{seed}:{a}:{b}".encode(), digest_size=8).digest()
        return int.from_bytes(digest, "big") / 2 ** 64

    def _preset_edges(self, order: list[int]) -> set[tuple[int, int]]:
        """Conexiones de la topología predefinida para una secuencia de asientos."""
        kind = self.config["topology"]
        n = len(order)
        edges: set[tuple[int, int]] = set()
        if n < 2:
            return edges

        if kind == "cadena":
            edges |= {(order[i], order[i + 1]) for i in range(n - 1)}

        elif kind == "anillo":
            edges |= {(order[i], order[(i + 1) % n]) for i in range(n)}

        elif kind in ("convergencia", "divergencia"):
            # Bloques de fan + 1 neuronas. En convergencia, las primeras fan de
            # cada bloque apuntan a la última; en divergencia, la primera apunta
            # a las demás. Con fan igual al total menos uno se recupera la
            # versión de un solo bloque: todas sobre una, o una sobre todas.
            fan = max(1, min(int(self.config.get("fan", 3)), n - 1))
            for start in range(0, n, fan + 1):
                block = order[start:start + fan + 1]
                if len(block) < 2:
                    continue
                if kind == "convergencia":
                    edges |= {(src, block[-1]) for src in block[:-1]}
                else:
                    edges |= {(block[0], dst) for dst in block[1:]}

        elif kind == "organica":
            seed = int(self.config.get("seed", 7))
            for src in order:
                scored = []
                for dst in order:
                    if dst == src:
                        continue
                    distance = abs(order.index(dst) - order.index(src))
                    # Probabilidad que cae con la distancia, más una pequeña
                    # probabilidad constante de atajos de largo alcance.
                    p = 0.32 * math.exp(-(distance - 1) / 2.0) + 0.015
                    u = self._uniform(seed, src, dst)
                    scored.append((u / p, u < p, dst))
                scored.sort()
                # Al menos una salida, para que la señal siempre pueda seguir;
                # hasta tres en total, para que el grafo siga siendo legible.
                chosen = [scored[0][2]] + [d for _, ok, d in scored[1:] if ok]
                edges |= {(src, dst) for dst in chosen[:3]}

        return edges

    def rebuild_edges(self) -> None:
        """Regenera las conexiones si la topología es predefinida.

        Se genera por separado dentro de cada circuito. En modo manual no se
        toca nada: las conexiones son decisión del operador.
        """
        if self.manual:
            return
        edges: set[tuple[int, int]] = set()
        groups = sorted({self.group_of(seat) for seat in self.seats()})
        for group in groups:
            order = [seat for seat in self.seats() if self.group_of(seat) == group]
            edges |= self._preset_edges(order)
        with self._lock:
            self.edges = edges

    def edit_edge(self, src: int, dst: int) -> str | None:
        """Agrega o quita la conexión src→dst y pasa a modo manual.

        Returns
        -------
        str or None
            Motivo del rechazo, o ``None`` si la edición se aplicó.
        """
        present = set(self.seats())
        if src == dst:
            return "Una neurona no puede conectarse consigo misma."
        if src not in present or dst not in present:
            return "Esa neurona ya no está conectada."
        if self.group_of(src) != self.group_of(dst):
            return "Con dos circuitos, las conexiones no pueden cruzar de uno a otro."
        with self._lock:
            self.manual = True
            self.config["topology"] = "manual"
            if (src, dst) in self.edges:
                self.edges.discard((src, dst))
            else:
                self.edges.add((src, dst))
        return None

    def by_seat(self, seat: int) -> Client | None:
        """Devuelve el cliente que ocupa un asiento."""
        with self._lock:
            for client in self.clients.values():
                if client.seat == seat:
                    return client
        return None

    # -- conducción -------------------------------------------------------

    def delay_ms(self, client: Client) -> float:
        """Retardo de conducción en milisegundos de reloj de pared.

        Longitud del axón entre velocidad de conducción, multiplicado por el
        factor de dilatación. Sin mielina la velocidad cae un orden de
        magnitud y el retardo crece en la misma proporción.
        """
        speed = (self.config["v_myelinated_ms"] if client.myelinated
                 else self.config["v_unmyelinated_ms"])
        real_ms = self.config["axon_length_m"] / speed * 1000.0
        return real_ms * self.config["dilation"]

    def relay_spike(self, sender: Client) -> None:
        """Entrega un potencial de acción a las neuronas postsinápticas."""
        targets = self.targets_of(sender.seat)
        delay = self.delay_ms(sender)
        sign = -1.0 if sender.polarity == "inhibitory" else 1.0
        weight = self.config["weight"] * sign

        for seat in targets:
            receiver = self.by_seat(seat)
            if receiver is None:
                continue
            payload = {
                "type": "input",
                "from_seat": sender.seat,
                "weight": round(weight, 4),
                "polarity": sender.polarity,
                "myelinated": sender.myelinated,
                "delay_ms": round(delay, 1),
            }
            # Un temporizador por entrega. A esta escala (decenas de
            # dispositivos, unidades de spikes por segundo) resulta más simple
            # que una cola con prioridad.
            threading.Timer(delay / 1000.0, receiver.send, args=(payload,)).start()

        event = {
            "type": "event",
            "kind": "spike",
            "seat": sender.seat,
            "targets": targets,
            "delay_ms": round(delay, 1),
            "polarity": sender.polarity,
            "myelinated": sender.myelinated,
            "t": time.time(),
        }
        self.broadcast(event, roles=("mural",))

    # -- juegos -----------------------------------------------------------

    def participants(self) -> list[Client]:
        """Neuronas conectadas que participan en el juego."""
        with self._lock:
            return [c for c in self.clients.values() if c.role == "neuron"]

    def start_game(self, kind: str, params: dict[str, Any]) -> None:
        """Inicia un juego colaborativo.

        En el juego de excitación contra inhibición los equipos se forman
        repartiendo los asientos en dos mitades y se bloquean los tipos, para
        que nadie cambie de equipo a mitad de la partida.
        """
        if kind not in GAME_DEFAULTS:
            return
        settings = {**GAME_DEFAULTS[kind]}
        for key in settings:
            if key in params:
                try:
                    settings[key] = float(params[key])
                except (TypeError, ValueError):
                    pass

        if kind == "tug":
            order = self.seats()
            half = (len(order) + 1) // 2
            for client in self.participants():
                if client.seat is not None:
                    client.polarity = ("excitatory" if order.index(client.seat) < half
                                       else "inhibitory")
                    client.send({"type": "polarity", "kind": client.polarity})
            self.config["locked"] = True

        with self._lock:
            self.game = {
                "kind": kind, "settings": settings, "started": time.time(),
                "taps": deque(), "rate": {}, "v": V_REST, "hits": 0,
                "quiet_until": 0.0, "count": {"excitatory": 0, "inhibitory": 0},
                "over": False, "winner": None,
            }

        self.broadcast_roster()
        self.broadcast_game()
        if kind == "tug":
            threading.Thread(target=self._tug_clock, args=(self.game,), daemon=True).start()

    def stop_game(self) -> None:
        """Detiene el juego en curso y libera el bloqueo de tipos."""
        with self._lock:
            self.game = None
        self.config["locked"] = False
        self.broadcast({"type": "game", "state": None})
        self.broadcast_roster()

    def on_tap(self, client: Client) -> None:
        """Registra un toque de una neurona durante un juego."""
        with self._lock:
            game = self.game
            if game is None or game["over"] or client.seat is None:
                return
            now = time.time()

            if game["kind"] == "sync":
                if now < game["quiet_until"]:
                    return
                window = game["settings"]["window_ms"] / 1000.0
                game["taps"].append((now, client.seat))
                while game["taps"] and now - game["taps"][0][0] > window:
                    game["taps"].popleft()
                distinct = len({seat for _, seat in game["taps"]})
                needed = self.quorum(game)
                fired = distinct >= needed
                if fired:
                    game["hits"] += 1
                    game["taps"].clear()
                    # Periodo refractario: evita contar dos veces la misma
                    # oleada de toques que llega ligeramente escalonada.
                    game["quiet_until"] = now + game["settings"]["refractory_ms"] / 1000.0

            else:  # tug
                stamps = game["rate"].setdefault(client.seat, deque())
                while stamps and now - stamps[0] > 1.0:
                    stamps.popleft()
                if len(stamps) >= game["settings"]["max_rate_hz"]:
                    return  # por encima del tope: no cuenta
                stamps.append(now)
                sign = 1.0 if client.polarity == "excitatory" else -1.0
                game["v"] = max(V_FLOOR, game["v"] + sign * game["settings"]["step_mv"])
                game["count"][client.polarity] += 1
                fired = game["v"] >= V_THRESHOLD
                if fired:
                    game["over"], game["winner"] = True, "excitatory"

        if fired:
            self.broadcast({"type": "game", "event": "fire",
                            "kind": game["kind"], "winner": game.get("winner")})
        self.broadcast_game()

    def quorum(self, game: dict[str, Any]) -> int:
        """Número de neuronas distintas que deben coincidir en la ventana."""
        return max(2, math.ceil(game["settings"]["quorum"] * len(self.participants())))

    def _tug_clock(self, game: dict[str, Any]) -> None:
        """Fuga del potencial compartido y límite de tiempo del juego."""
        dt = 0.1
        while True:
            time.sleep(dt)
            with self._lock:
                if self.game is not game or game["over"]:
                    return
                tau = game["settings"]["tau_ms"] / 1000.0
                game["v"] += (V_REST - game["v"]) * dt / tau
                elapsed = time.time() - game["started"]
                timeout = elapsed >= game["settings"]["duration_s"]
                if timeout:
                    # Si el tiempo se agota sin alcanzar el umbral, la
                    # inhibición logró sostener a la neurona por debajo.
                    game["over"], game["winner"] = True, "inhibitory"
            if timeout:
                self.broadcast({"type": "game", "event": "end",
                                "kind": "tug", "winner": "inhibitory"})
            self.broadcast_game()
            if timeout:
                return

    def game_state(self) -> dict[str, Any] | None:
        """Estado del juego, en la forma que consumen el mural y los clientes."""
        with self._lock:
            game = self.game
            if game is None:
                return None
            state = {"kind": game["kind"], "over": game["over"],
                     "winner": game["winner"]}
            if game["kind"] == "sync":
                state.update({
                    "in_window": len({seat for _, seat in game["taps"]}),
                    "quorum": self.quorum(game), "hits": game["hits"],
                    "window_ms": game["settings"]["window_ms"],
                })
            else:
                elapsed = time.time() - game["started"]
                state.update({
                    "v": round(game["v"], 2), "threshold": V_THRESHOLD,
                    "rest": V_REST, "floor": V_FLOOR,
                    "remaining_s": round(max(0.0, game["settings"]["duration_s"] - elapsed), 1),
                    "count": dict(game["count"]),
                })
            return state

    def broadcast_game(self) -> None:
        """Difunde el estado del juego a todos los clientes."""
        self.broadcast({"type": "game", "state": self.game_state()})

    # -- difusión ---------------------------------------------------------

    def broadcast(self, message: dict[str, Any],
                  roles: tuple[str, ...] | None = None) -> None:
        """Envía un mensaje a todos los clientes, o solo a ciertos roles."""
        with self._lock:
            targets = [c for c in self.clients.values()
                       if roles is None or c.role in roles]
        for client in targets:
            client.send(message)

    def broadcast_roster(self) -> None:
        """Publica el censo de neuronas y la configuración vigente."""
        with self._lock:
            neurons = sorted(
                ({"seat": c.seat, "id": c.cid, "myelinated": c.myelinated,
                  "polarity": c.polarity, "group": c.group,
                  "vm": round(c.last_vm, 2)}
                 for c in self.clients.values() if c.role == "neuron"),
                key=lambda n: n["seat"] or 0,
            )
        message = {
            "type": "roster",
            "neurons": neurons,
            "config": self.config,
            "edges": [[seat, target]
                      for seat in self.seats()
                      for target in self.targets_of(seat)],
        }
        self.broadcast(message)

        # Los destinos de cada neurona cambian con el censo. El welcome pudo
        # haberse enviado cuando era la única conectada, con lista vacía, por
        # lo que hay que reenviarlos en cada alta o baja.
        with self._lock:
            neurons = [c for c in self.clients.values() if c.role == "neuron"]
        for client in neurons:
            client.send({"type": "targets", "seat": client.seat,
                         "targets": self.targets_of(client.seat)})

    # -- mensajes entrantes ----------------------------------------------

    def handle(self, client: Client, message: dict[str, Any]) -> None:
        """Despacha un mensaje ya deserializado."""
        kind = message.get("type")

        if kind == "spike" and client.role == "neuron":
            self.relay_spike(client)

        elif kind == "vm":
            try:
                client.last_vm = float(message.get("v", -70.0))
            except (TypeError, ValueError):
                pass
            else:
                # Solo a los murales. El censo completo se difunde únicamente
                # ante cambios estructurales; el voltaje se actualiza tres
                # veces por segundo y difundirlo a todos sería redundante.
                if client.seat is not None:
                    self.broadcast({"type": "vm", "seat": client.seat,
                                    "v": client.last_vm}, roles=("mural",))

        elif kind == "myelin":
            # El bloqueo se aplica en el servidor y no solo en la interfaz:
            # ocultar un botón no impide que alguien mande el mensaje.
            if client.role == "neuron" and self.config.get("locked"):
                client.send({"type": "locked", "reason": "myelin"})
                return
            target = client
            if "seat" in message and client.role == "mural":
                target = self.by_seat(int(message["seat"])) or client
            target.myelinated = bool(message.get("on", True))
            if target is not client:
                target.send({"type": "myelin", "on": target.myelinated})
            self.broadcast_roster()

        elif kind == "polarity":
            if client.role == "neuron" and self.config.get("locked"):
                client.send({"type": "locked", "reason": "polarity"})
                return
            wanted = message.get("kind")
            if wanted in ("excitatory", "inhibitory"):
                # Puede venir del propio dispositivo o del mural, que indica
                # el asiento al que se refiere.
                target = client
                if "seat" in message and client.role == "mural":
                    target = self.by_seat(int(message["seat"])) or client
                target.polarity = wanted
                target.send({"type": "polarity", "kind": wanted})
                self.broadcast_roster()

        elif kind == "config":
            changed = False
            for key in ("dilation", "weight", "axon_length_m",
                        "v_myelinated_ms", "v_unmyelinated_ms"):
                if key in message:
                    try:
                        self.config[key] = float(message[key])
                        changed = True
                    except (TypeError, ValueError):
                        pass
            if message.get("topology") in TOPOLOGIES:
                self.config["topology"] = message["topology"]
                self.manual = False
                changed = True
            if "fan" in message:
                try:
                    self.config["fan"] = max(1, min(MAX_FAN, int(message["fan"])))
                    changed = True
                except (TypeError, ValueError):
                    pass
            if "groups" in message:
                self.config["groups"] = max(1, min(2, int(message["groups"])))
                self.regroup()
                changed = True
            if changed:
                self.rebuild_edges()
            if "locked" in message:
                self.config["locked"] = bool(message["locked"])
                changed = True
            if changed:
                self.broadcast_roster()
                for c in list(self.clients.values()):
                    if c.role == "neuron":
                        c.send({"type": "welcome", "id": c.cid, "seat": c.seat,
                                "role": c.role, "polarity": c.polarity,
                                "group": c.group, "config": self.config,
                                "targets": self.targets_of(c.seat)})

        elif kind == "reset":
            self.broadcast({"type": "reset"}, roles=("neuron",))

        elif kind == "edge" and client.role == "mural":
            try:
                reason = self.edit_edge(int(message["from"]), int(message["to"]))
            except (KeyError, TypeError, ValueError):
                reason = "Conexión inválida."
            if reason:
                client.send({"type": "notice", "text": reason})
            self.broadcast_roster()

        elif kind == "edges" and client.role == "mural":
            if message.get("op") == "clear":
                with self._lock:
                    self.manual = True
                    self.config["topology"] = "manual"
                    self.edges = set()
                self.broadcast_roster()

        elif kind == "tap" and client.role == "neuron":
            # El toque se reenvía al mural haya juego o no: es la entrada
            # sináptica con la que se construye la onda de la sala.
            if client.seat is not None:
                self.broadcast({"type": "tap", "seat": client.seat}, roles=("mural",))
            self.on_tap(client)

        elif kind == "game" and client.role == "mural":
            if message.get("action") == "start":
                self.start_game(str(message.get("kind")), message)
            elif message.get("action") == "stop":
                self.stop_game()


# ---------------------------------------------------------------------------
# Manejador HTTP con promoción a WebSocket
# ---------------------------------------------------------------------------

class RoomHandler(SimpleHTTPRequestHandler):
    """Sirve los archivos de la sala y promueve ``/ws`` a WebSocket."""

    hub: Hub  # inyectado con functools.partial

    protocol_version = "HTTP/1.1"

    # Rutas cortas: reducen la densidad del QR que se imprime para la sala.
    # Mapear "/" también evita el listado de directorio de la clase base.
    ALIASES = {
        "/": "/neurona.html",
        "/n": "/neurona.html",
        "/m": "/mural.html",
    }

    def log_message(self, fmt: str, *args: Any) -> None:
        """Silencia el registro de cada archivo servido."""
        if "/ws" in (self.path or ""):
            super().log_message(fmt, *args)

    def do_GET(self) -> None:  # noqa: N802  (nombre impuesto por la clase base)
        """Atiende un GET, o toma la conexión si pide upgrade a WebSocket."""
        upgrade = (self.headers.get("Upgrade") or "").lower()
        if self.path.split("?")[0] == "/ws" and upgrade == "websocket":
            self.handle_websocket()
            return

        path, _, query = self.path.partition("?")
        if path in self.ALIASES:
            self.path = self.ALIASES[path] + (f"?{query}" if query else "")

        # Sin caché: en la sala se itera y no se quiere depurar versiones
        # viejas guardadas por el navegador.
        super().do_GET()

    def end_headers(self) -> None:
        """Agrega cabeceras anti-caché a toda respuesta estática."""
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def handle_websocket(self) -> None:
        """Completa el handshake y atiende el flujo de frames."""
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "falta Sec-WebSocket-Key")
            return

        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key(key))
        # Obligatorio: send_response y send_header solo acumulan en un búfer;
        # end_headers es lo que lo escribe. Sin esta llamada el cliente recibe
        # una respuesta vacía y el handshake falla.
        self.end_headers()

        sock = self.connection
        sock.settimeout(None)
        reader = self.rfile

        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        params = dict(part.split("=", 1) for part in query.split("&") if "=" in part)
        role = "mural" if params.get("role") == "mural" else "neuron"
        seat = int(params["seat"]) if params.get("seat", "").isdigit() else None

        client = self.hub.join(sock, role, seat)

        try:
            while client.alive:
                opcode, payload = read_frame(reader)

                if opcode == OP_CLOSE:
                    break
                if opcode == OP_PING:
                    with client._lock:  # noqa: SLF001  (mismo módulo)
                        sock.sendall(encode_frame(payload, OP_PONG))
                    continue
                if opcode == OP_PONG:
                    continue
                if opcode != OP_TEXT:
                    continue

                try:
                    message = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(message, dict):
                    self.hub.handle(client, message)

        except (ConnectionError, OSError, struct.error):
            pass
        finally:
            self.hub.leave(client)
            self.close_connection = True


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------

def network_warnings(port: int) -> list[str]:
    """Detecta en Windows lo que impide que otros dispositivos se conecten.

    El síntoma de estos problemas es engañoso: el servidor arranca bien y
    responde desde la propia laptop, pero los teléfonos nunca llegan. El
    registro del servidor solo muestra conexiones de la IP local.

    Returns
    -------
    list of str
        Advertencias con el comando que las resuelve; vacía si todo está bien
        o si no se está en Windows.
    """
    if os.name != "nt":
        return []
    warnings: list[str] = []

    # Regla de firewall por puerto. Las reglas por programa no bastan: el
    # Python de un entorno virtual es un ejecutable distinto del Python del
    # sistema, y el permiso concedido a uno no cubre al otro.
    try:
        rule = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", "name=Sala DUNNE"],
            capture_output=True, text=True, timeout=6)
        if rule.returncode != 0:
            warnings.append(
                "No existe la regla de firewall 'Sala DUNNE'. Los teléfonos no podrán "
                "conectarse. En una terminal como administrador:\n"
                f'    netsh advfirewall firewall add rule name="Sala DUNNE" dir=in '
                f"action=allow protocol=TCP localport={port}")
    except (OSError, subprocess.SubprocessError):
        pass

    # Perfil de red. En una red marcada como pública, Windows bloquea casi
    # toda conexión entrante aunque exista la regla.
    try:
        profile = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetConnectionProfile | Select-Object -First 1).NetworkCategory"],
            capture_output=True, text=True, timeout=8)
        if profile.stdout.strip().lower() == "public":
            warnings.append(
                "La red está marcada como Pública. Cámbiala a Privada en la "
                "configuración de wifi, o como administrador:\n"
                "    Set-NetConnectionProfile -NetworkCategory Private")
    except (OSError, subprocess.SubprocessError):
        pass

    return warnings


def local_ips() -> list[str]:
    """Direcciones IPv4 locales plausibles para compartir en la sala."""
    found: list[str] = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))          # no envía nada, solo enruta
        found.append(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127.") and address not in found:
                found.append(address)
    except OSError:
        pass
    return found


def serve(host: str, port: int, directory: Path,
          config: dict[str, Any] | None = None) -> ThreadingHTTPServer:
    """Levanta el servidor y devuelve la instancia, ya escuchando."""
    hub = Hub(config)

    # El manejador recibe el hub como atributo de clase porque
    # ThreadingHTTPServer instancia la clase por cada conexión y no acepta
    # pasarle argumentos propios.
    class Bound(RoomHandler):
        pass

    Bound.hub = hub

    server = ThreadingHTTPServer((host, port), partial(Bound, directory=str(directory)))
    server.daemon_threads = True
    server.hub = hub                             # para pruebas e inspección
    return server


def main() -> int:
    """Punto de entrada de línea de comandos."""
    ap = argparse.ArgumentParser(description="Servidor de la sala DUNNE.")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--dir", type=Path, default=Path(__file__).parent)
    ap.add_argument("--topology", choices=TOPOLOGIES, default="organica")
    ap.add_argument("--dilation", type=float, default=DEFAULT_CONFIG["dilation"])
    args = ap.parse_args()

    server = serve(args.host, args.port, args.dir,
                   {"topology": args.topology, "dilation": args.dilation})

    print(f"Sala DUNNE en el puerto {args.port}, sirviendo {args.dir}")
    print(f"topología: {args.topology} · dilatación temporal: ×{args.dilation:g}")
    for ip in local_ips():
        print(f"  neuronas → http://{ip}:{args.port}/n")
        print(f"  mural    → http://{ip}:{args.port}/m")
    for warning in network_warnings(args.port):
        print(f"\nAVISO · {warning}")
    print(f"\nPython en uso: {sys.executable}")
    print("Ctrl+C para detener.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\ndeteniendo…")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

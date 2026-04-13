import socket
import time

from protocol import (
    Message, Opcode, ProtocolError,
    msg_set_state, msg_start_game, msg_stop_game, msg_get_state
)


# ============================================================
# CONFIGURAZIONE
# ============================================================

SERVER_IP   = "192.168.5.62"
SERVER_PORT = 8888


# ============================================================
# PROTOCOL CLIENT
# ============================================================

class ProtocolClient:
    """Client TCP per comunicare con il server tramite il protocollo a 2 byte.

    Supporta il context manager (with), quindi la connessione viene
    chiusa automaticamente anche in caso di eccezione.

        with ProtocolClient(SERVER_IP, SERVER_PORT) as c:
            c.set_state(0b10101)
    """

    def __init__(self, host: str, port: int):
        self.host  = host
        self.port  = port
        self._sock = None

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((self.host, self.port))
        print(f"[CLIENT] connesso a {self.host}:{self.port}")

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None
            print("[CLIENT] disconnesso")

    # --- Context manager ---

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    # --- Invio/ricezione raw ---

    def _send(self, msg: Message):
        """Invia un messaggio e, se l'opcode prevede una risposta, la legge e la restituisce."""
        self._sock.sendall(msg.encode())
        print(f"[TX] {msg}")

        # solo GET_STATE genera una risposta dal server
        if msg.opcode == Opcode.GET_STATE:
            data = self._sock.recv(Message.SIZE)
            response = Message.decode(data)
            print(f"[RX] {response}")
            return response

        return None

    # --- API pubblica ---

    def set_state(self, bitmask: int):
        """Imposta i LED tramite bitmask (bit 0–4 = LED 0–4)."""
        self._send(msg_set_state(bitmask))

    def start_game(self, game_id: int):
        """Avvia il gioco con l'ID specificato (0–3)."""
        self._send(msg_start_game(game_id))

    def stop_game(self):
        """Ferma il gioco in corso."""
        self._send(msg_stop_game())

    def get_state(self) -> int:
        """Chiede al server lo stato corrente dei LED; restituisce la bitmask."""
        response = self._send(msg_get_state())
        if response and response.opcode == Opcode.SET_STATE:
            return response.payload
        return 0x00


# ============================================================
# MENU INTERATTIVO
# ============================================================

# Nomi dei giochi — specchiati rispetto a GameEngine in server.py
GAMES = {
    0:  ("Chase",         "luce che scorre da sinistra a destra"),
    1:  ("Blink",         "tutti i LED lampeggiano insieme"),
    2:  ("Alternating",   "pattern 10101 / 01010 alternato"),
    3:  ("Binary count",  "conta in binario da 0 a 31"),
    4:  ("Bounce",        "ping pong avanti e indietro"),
    5:  ("Random",        "combinazione casuale ogni 150ms"),
    6:  ("Fill & drain",  "riempie da sinistra poi svuota"),
    7:  ("SOS",           "· · · — — — · · · in Morse"),
    8:  ("Heartbeat",     "doppio flash + lunga pausa"),
    9:  ("Inside out",    "si espande dal centro ai bordi"),
    10: ("Knight Rider",  "bounce con scia di 2 LED"),
    11: ("Police",        "sinistra e destra in alternanza"),
    12: ("Strobe",        "blink velocissimo (effetto discoteca)"),
    13: ("Snake",         "chase con scia di 2 LED"),
    14: ("Twinkle",       "LED casuali che lampeggiano in modo irregolare"),
    15: ("Wipe",          "accende e spegne nella stessa direzione"),
    16: ("Pairs",         "bordi → interni → centro a turno"),
    17: ("Morse CIAO",    "scrive CIAO in codice Morse"),
    18: ("Dice",          "simula il lancio di un dado 1–5"),
    19: ("Binary clock",  "mostra i secondi correnti in binario"),
    20: ("Outside in",    "si comprime dai bordi verso il centro"),
    21: ("Zip",           "due punti si incrociano al centro"),
    22: ("Fireworks",     "esplosioni di luce casuali"),
    23: ("Morse LUCE",    "scrive LUCE in codice Morse"),
}

MENU_PRINCIPALE = """
╔══════════════════════════════════════╗
║         PROTOCOLLO 2 BYTE            ║
╠══════════════════════════════════════╣
║  s  → SET_STATE  (inserisci bitmask) ║
║  j  → menu GIOCHI                    ║
║  x  → STOP_GAME                      ║
║  g  → GET_STATE                      ║
║  q  → esci                           ║
╚══════════════════════════════════════╝
"""

def _build_game_menu() -> str:
    """Costruisce dinamicamente il menu dei giochi dalla lista GAMES."""
    righe = ["", "╔══════════════════════════════════════════════════╗"]
    righe.append(   "║               GIOCHI DI LUCE                    ║")
    righe.append(   "╠══════════════════════════════════════════════════╣")
    for game_id, (nome, desc) in GAMES.items():
        riga = f"  {game_id}  {nome:<14} — {desc}"
        righe.append(f"║{riga:<50}║")
    righe.append(   "╠══════════════════════════════════════════════════╣")
    righe.append(   "║  b  → torna al menu principale                   ║")
    righe.append(   "╚══════════════════════════════════════════════════╝")
    return "\n".join(righe)

MENU_GIOCHI = _build_game_menu()

GAME_IDS = {str(k) for k in GAMES}


def _menu_giochi(client: ProtocolClient):
    print(MENU_GIOCHI)

    while True:
        scelta = input("gioco >>> ").strip().lower()

        if scelta == "b":
            break

        elif scelta in GAME_IDS:
            client.start_game(int(scelta))

        else:
            print("    ID non valido — scegli un numero dal menu oppure 'b' per tornare")


def run_menu(client: ProtocolClient):
    print(MENU_PRINCIPALE)

    while True:
        scelta = input(">>> ").strip().lower()

        if scelta == "q":
            break

        elif scelta == "s":
            raw = input("    bitmask (es. 10101 oppure 0x15): ").strip()
            try:
                # accetta binario (10101), hex (0x15) o decimale (21)
                if raw.startswith("0x") or raw.startswith("0X"):
                    valore = int(raw, 16)
                elif all(c in "01" for c in raw):
                    valore = int(raw, 2)
                else:
                    valore = int(raw)
                client.set_state(valore)
            except ValueError:
                print("    valore non valido")

        elif scelta == "j":
            _menu_giochi(client)
            print(MENU_PRINCIPALE)

        elif scelta == "x":
            client.stop_game()

        elif scelta == "g":
            state = client.get_state()
            print(f"    Stato LED: {state:05b}  (0x{state:02X})")

        else:
            print("    shortcut non riconosciuta — riprova")


if __name__ == "__main__":
    with ProtocolClient(SERVER_IP, SERVER_PORT) as client:
        run_menu(client)

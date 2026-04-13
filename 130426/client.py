import socket
import time

from protocol import (
    Message, Opcode, ProtocolError,
    msg_set_state, msg_start_game, msg_stop_game, msg_get_state
)


# ============================================================
# CONFIGURAZIONE
# ============================================================

SERVER_IP   = "192.168.5.55"
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
# DEMO
# ============================================================

if __name__ == "__main__":

    with ProtocolClient(SERVER_IP, SERVER_PORT) as client:

        print("\n--- SET_STATE: accendi LED 0, 2, 4 (bitmask 10101) ---")
        client.set_state(0b10101)
        time.sleep(1)

        print("\n--- START_GAME 0: chase ---")
        client.start_game(0)
        time.sleep(3)

        print("\n--- START_GAME 1: blink (sovrascrive il precedente) ---")
        client.start_game(1)
        time.sleep(3)

        print("\n--- STOP_GAME ---")
        client.stop_game()
        time.sleep(0.5)

        print("\n--- GET_STATE ---")
        state = client.get_state()
        print(f"    Stato LED: {state:05b}  (0x{state:02X})")

        print("\n--- SET_STATE: spegni tutto ---")
        client.set_state(0x00)

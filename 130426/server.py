import socket
import threading
import time
import random

from gpiozero import LED
from signal import pause

from protocol import Opcode, Message, ProtocolError, msg_set_state


# ============================================================
# CONFIGURAZIONE
# ============================================================

HOST = "0.0.0.0"   # accetta connessioni da qualsiasi interfaccia
PORT = 8888

# I 5 LED sono mappati sui pin GPIO in ordine:
# LED 0 → pin 17 (bit 0 della bitmask)
# LED 1 → pin 27 (bit 1)
# LED 2 → pin 22 (bit 2)
# LED 3 → pin 23 (bit 3)
# LED 4 → pin 24 (bit 4)
LED_PINS = [17, 27, 22, 23, 24]


# ============================================================
# LED BANK — gestisce il banco di LED tramite bitmask
# ============================================================

class LEDBank:
    """Astrae un gruppo di LED fisici in un unico oggetto controllabile via bitmask."""

    def __init__(self, pins: list):
        self._leds  = [LED(p) for p in pins]
        self._state = 0x00  # stato corrente, utile per rispondere a GET_STATE

    def set_state(self, bitmask: int):
        """Imposta lo stato di tutti i LED in un colpo solo.

        Il bit N della bitmask controlla il LED N:
        se il bit è 1 il LED si accende, se è 0 si spegne.
        """
        self._state = bitmask & 0xFF
        for i, led in enumerate(self._leds):
            if bitmask & (1 << i):
                led.on()
            else:
                led.off()

    def get_state(self) -> int:
        return self._state

    def all_off(self):
        self.set_state(0x00)

    def all_on(self):
        # accende tutti: una maschera con tanti 1 quanti sono i LED
        self.set_state((1 << len(self._leds)) - 1)


# ============================================================
# GAME ENGINE — esegue i giochi di luce in un thread dedicato
# ============================================================

class GameEngine:
    """Gestisce i giochi di luce.

    Ogni gioco gira in un thread separato. Per fermarlo si usa
    lo stesso pattern stop_event visto in thread.py (160326):
    un threading.Event fa da "bandierina" che il loop controlla
    ad ogni iterazione.
    """

    def __init__(self, bank: LEDBank):
        self.bank    = bank
        self._thread = None
        self._stop   = threading.Event()

        # mappa game_id → metodo di gioco (bound method, non serve passare self)
        self._games = {
            0: self._game_chase,
            1: self._game_blink,
            2: self._game_alternating,
            3: self._game_binary_count,
            4: self._game_bounce,
            5: self._game_random,
            6: self._game_fill_drain,
            7: self._game_sos,
            8: self._game_heartbeat,
            9: self._game_inside_out,
        }

    def _sleep(self, seconds: float):
        """Sleep interrompibile: si sveglia subito se lo stop è richiesto.

        Stesso trucco usato in SOSController._sleep_interrompibile (160326).
        """
        self._stop.wait(timeout=seconds)

    # --- Giochi ---

    def _game_chase(self):
        """Gioco 0: luce che scorre da sinistra a destra in loop."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            for i in range(n):
                if self._stop.is_set():
                    break
                self.bank.set_state(1 << i)
                self._sleep(0.15)

    def _game_blink(self):
        """Gioco 1: tutti i LED lampeggiano insieme."""
        while not self._stop.is_set():
            self.bank.all_on()
            self._sleep(0.3)
            self.bank.all_off()
            self._sleep(0.3)

    def _game_alternating(self):
        """Gioco 2: pattern alternato 10101 / 01010."""
        while not self._stop.is_set():
            self.bank.set_state(0b10101)
            self._sleep(0.4)
            self.bank.set_state(0b01010)
            self._sleep(0.4)

    def _game_binary_count(self):
        """Gioco 3: conta in binario da 0 a 31 sui 5 LED."""
        while not self._stop.is_set():
            for n in range(32):
                if self._stop.is_set():
                    break
                self.bank.set_state(n)
                self._sleep(0.12)

    def _game_bounce(self):
        """Gioco 4: ping pong — il punto di luce va avanti e indietro."""
        n = len(self.bank._leds)
        # costruiamo la sequenza: 0,1,2,3,4,3,2,1 (i bordi non si ripetono)
        sequenza = list(range(n)) + list(range(n - 2, 0, -1))
        while not self._stop.is_set():
            for i in sequenza:
                if self._stop.is_set():
                    break
                self.bank.set_state(1 << i)
                self._sleep(0.1)

    def _game_random(self):
        """Gioco 5: accende una combinazione casuale di LED ogni 150ms."""
        n = len(self.bank._leds)
        max_mask = (1 << n) - 1
        while not self._stop.is_set():
            self.bank.set_state(random.randint(0, max_mask))
            self._sleep(0.15)

    def _game_fill_drain(self):
        """Gioco 6: riempie i LED uno alla volta da sinistra, poi li spegne da destra."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            # riempi: a ogni passo accendiamo un LED in più
            for i in range(n):
                if self._stop.is_set():
                    break
                self.bank.set_state((1 << (i + 1)) - 1)
                self._sleep(0.2)
            # svuota: a ogni passo spegniamo il LED più a destra ancora acceso
            for i in range(n - 1, -1, -1):
                if self._stop.is_set():
                    break
                self.bank.set_state((1 << i) - 1)
                self._sleep(0.2)

    def _game_sos(self):
        """Gioco 7: segnale SOS in codice Morse (· · · — — — · · ·) con tutti i LED.

        Omaggio a 160326/thread.py — stessa logica, ma su tutti i LED in parallelo.
        """
        while not self._stop.is_set():
            for _ in range(3):          # S — tre brevi
                if self._stop.is_set(): break
                self.bank.all_on();  self._sleep(0.2)
                self.bank.all_off(); self._sleep(0.2)
            for _ in range(3):          # O — tre lunghi
                if self._stop.is_set(): break
                self.bank.all_on();  self._sleep(0.6)
                self.bank.all_off(); self._sleep(0.2)
            for _ in range(3):          # S — tre brevi
                if self._stop.is_set(): break
                self.bank.all_on();  self._sleep(0.2)
                self.bank.all_off(); self._sleep(0.2)
            self._sleep(1.0)            # pausa tra una ripetizione e l'altra

    def _game_heartbeat(self):
        """Gioco 8: doppio flash rapido seguito da una lunga pausa (battito cardiaco)."""
        while not self._stop.is_set():
            self.bank.all_on();  self._sleep(0.08)   # primo battito
            self.bank.all_off(); self._sleep(0.12)
            self.bank.all_on();  self._sleep(0.08)   # secondo battito
            self.bank.all_off(); self._sleep(0.8)    # diastole

    def _game_inside_out(self):
        """Gioco 9: si espande dal LED centrale verso i bordi e poi si ricomprime."""
        n   = len(self.bank._leds)
        mid = n // 2

        # costruiamo le maschere di espansione una volta sola
        expand = []
        for r in range(mid + 1):
            mask = 0
            for i in range(mid - r, mid + r + 1):
                if 0 <= i < n:
                    mask |= (1 << i)
            expand.append(mask)

        # la contrazione è l'espansione al contrario (senza ripetere il centro)
        contract = list(reversed(expand))
        sequenza = expand + contract[1:]

        while not self._stop.is_set():
            for mask in sequenza:
                if self._stop.is_set():
                    break
                self.bank.set_state(mask)
                self._sleep(0.15)

    # --- Controllo ---

    def start(self, game_id: int):
        # se c'è già un gioco in corso lo fermiamo prima di avviarne uno nuovo
        self.stop()

        game_fn = self._games.get(game_id)
        if game_fn is None:
            print(f"[GAME] gioco {game_id} non esiste")
            return

        self._stop.clear()
        self._thread = threading.Thread(target=game_fn, daemon=True)
        self._thread.start()
        print(f"[GAME] avviato gioco {game_id}")

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join()
            self.bank.all_off()
            print("[GAME] gioco fermato")


# ============================================================
# PROTOCOL SERVER — accetta connessioni e fa il dispatch
# ============================================================

class ProtocolServer:
    """Server TCP che interpreta il protocollo a 2 byte e controlla LED e giochi.

    Può gestire più client in contemporanea: ogni connessione
    viene affidata a un thread separato.
    """

    def __init__(self, host: str, port: int, led_pins: list):
        self.host   = host
        self.port   = port
        self.bank   = LEDBank(led_pins)
        self.engine = GameEngine(self.bank)

    def _dispatch(self, msg: Message):
        """Esegue l'azione corrispondente all'opcode ricevuto.

        Restituisce un Message di risposta se il comando lo richiede,
        None altrimenti.
        """
        if msg.opcode == Opcode.SET_STATE:
            self.bank.set_state(msg.payload)
            print(f"[SET_STATE] bitmask = {msg.payload:05b}")
            return None

        elif msg.opcode == Opcode.START_GAME:
            self.engine.start(msg.payload)
            return None

        elif msg.opcode == Opcode.STOP_GAME:
            self.engine.stop()
            return None

        elif msg.opcode == Opcode.GET_STATE:
            state = self.bank.get_state()
            print(f"[GET_STATE] stato corrente = {state:05b}")
            # il server risponde con SET_STATE + bitmask attuale
            return msg_set_state(state)

        return None

    def _handle_client(self, conn: socket.socket, addr):
        print(f"[CONN] connesso: {addr}")

        try:
            while True:
                data = conn.recv(Message.SIZE)
                if not data:
                    # il client ha chiuso la connessione
                    break

                try:
                    msg = Message.decode(data)
                    print(f"[RX] {msg}")

                    response = self._dispatch(msg)
                    if response:
                        conn.sendall(response.encode())
                        print(f"[TX] {response}")

                except ProtocolError as e:
                    # opcode sconosciuto: lo logghiamo e andiamo avanti
                    print(f"[ERR] {e}")

        except ConnectionResetError:
            pass
        finally:
            conn.close()
            print(f"[CONN] disconnesso: {addr}")

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((self.host, self.port))
            srv.listen()
            print(f"[SERVER] in ascolto su {self.host}:{self.port}")

            while True:
                conn, addr = srv.accept()
                t = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                t.start()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    server = ProtocolServer(HOST, PORT, LED_PINS)
    server.run()

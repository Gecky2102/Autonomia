import socket
import threading
import time
import random

try:
    from gpiozero import LED
    GPIO_AVAILABLE = True
except (ImportError, Exception):
    GPIO_AVAILABLE = False

    # LED finto: usato quando gpiozero non è disponibile (es. su PC senza GPIO)
    class LED:
        def __init__(self, pin):
            self.pin = pin
        def on(self):
            print(f"  [mock] LED pin {self.pin:2d} → ON")
        def off(self):
            print(f"  [mock] LED pin {self.pin:2d} → OFF")

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
            0:  self._game_chase,
            1:  self._game_blink,
            2:  self._game_alternating,
            3:  self._game_binary_count,
            4:  self._game_bounce,
            5:  self._game_random,
            6:  self._game_fill_drain,
            7:  self._game_sos,
            8:  self._game_heartbeat,
            9:  self._game_inside_out,
            10: self._game_knight_rider,
            11: self._game_police,
            12: self._game_strobe,
            13: self._game_snake,
            14: self._game_twinkle,
            15: self._game_wipe,
            16: self._game_pairs,
            17: self._game_morse_ciao,
            18: self._game_dice,
            19: self._game_binary_clock,
            20: self._game_outside_in,
            21: self._game_zip,
            22: self._game_fireworks,
            23: self._game_morse_luce,
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

    def _game_knight_rider(self):
        """Gioco 10: Knight Rider — punto luminoso che rimbalza con scia di 2 LED."""
        n = len(self.bank._leds)
        sequenza = list(range(n)) + list(range(n - 2, 0, -1))
        prev = None
        while not self._stop.is_set():
            for i in sequenza:
                if self._stop.is_set(): break
                mask = (1 << i) | (1 << prev if prev is not None else 0)
                self.bank.set_state(mask)
                prev = i
                self._sleep(0.08)

    def _game_police(self):
        """Gioco 11: luci della polizia — sinistra e destra lampeggiano in alternanza."""
        sinistra = 0b00011   # LED 0 e 1
        destra   = 0b11000   # LED 3 e 4
        while not self._stop.is_set():
            for _ in range(3):
                if self._stop.is_set(): break
                self.bank.set_state(sinistra); self._sleep(0.08)
                self.bank.all_off();           self._sleep(0.05)
            for _ in range(3):
                if self._stop.is_set(): break
                self.bank.set_state(destra);   self._sleep(0.08)
                self.bank.all_off();           self._sleep(0.05)
            self._sleep(0.2)

    def _game_strobe(self):
        """Gioco 12: strobo — blink velocissimo (effetto discoteca)."""
        while not self._stop.is_set():
            self.bank.all_on();  self._sleep(0.04)
            self.bank.all_off(); self._sleep(0.04)

    def _game_snake(self):
        """Gioco 13: snake — chase con scia di 2 LED."""
        n = len(self.bank._leds)
        sequenza = list(range(n)) + list(range(n - 2, 0, -1))
        while not self._stop.is_set():
            for idx, i in enumerate(sequenza):
                if self._stop.is_set(): break
                mask = 1 << i
                if idx > 0:
                    mask |= 1 << sequenza[idx - 1]
                self.bank.set_state(mask)
                self._sleep(0.1)

    def _game_twinkle(self):
        """Gioco 14: twinkle — LED casuali che lampeggiano brevemente e in modo irregolare."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            led = random.randint(0, n - 1)
            self.bank.set_state(1 << led)
            self._sleep(0.08)
            self.bank.all_off()
            self._sleep(random.uniform(0.05, 0.25))

    def _game_wipe(self):
        """Gioco 15: wipe — accende da sinistra a destra, poi spegne nello stesso verso."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            mask = 0
            for i in range(n):          # accendi da sinistra
                if self._stop.is_set(): break
                mask |= (1 << i)
                self.bank.set_state(mask)
                self._sleep(0.15)
            for i in range(n):          # spegni da sinistra
                if self._stop.is_set(): break
                mask &= ~(1 << i)
                self.bank.set_state(mask)
                self._sleep(0.15)

    def _game_pairs(self):
        """Gioco 16: coppie — (bordi), (interni), (centro) lampeggiano a turno."""
        coppie = [0b10001, 0b01010, 0b00100]   # bordi → interni → centro
        while not self._stop.is_set():
            for mask in coppie:
                if self._stop.is_set(): break
                self.bank.set_state(mask)
                self._sleep(0.35)
            self.bank.all_off()
            self._sleep(0.15)

    def _game_morse_ciao(self):
        """Gioco 17: scrive CIAO in codice Morse con tutti i LED."""
        DIT = 0.2
        DAH = 0.6
        SEP = 0.2    # pausa tra simboli della stessa lettera
        LET = 0.5    # pausa tra lettere
        WRD = 1.2    # pausa tra ripetizioni della parola

        MORSE = {
            'C': [DAH, DIT, DAH, DIT],
            'I': [DIT, DIT],
            'A': [DIT, DAH],
            'O': [DAH, DAH, DAH],
        }

        while not self._stop.is_set():
            for simboli in MORSE.values():
                for durata in simboli:
                    if self._stop.is_set(): break
                    self.bank.all_on();  self._sleep(durata)
                    self.bank.all_off(); self._sleep(SEP)
                self._sleep(LET)
            self._sleep(WRD)

    def _game_dice(self):
        """Gioco 18: dado — agitazione casuale poi risultato 1–5 (N LED accesi da sinistra)."""
        n       = len(self.bank._leds)
        max_val = (1 << n) - 1
        while not self._stop.is_set():
            for _ in range(12):         # agitazione
                if self._stop.is_set(): break
                self.bank.set_state(random.randint(1, max_val))
                self._sleep(0.07)
            if self._stop.is_set(): break
            risultato = random.randint(1, n)
            self.bank.set_state((1 << risultato) - 1)   # N LED accesi
            self._sleep(2.0)

    def _game_binary_clock(self):
        """Gioco 19: orologio binario — mostra i secondi correnti mod 32 in binario."""
        while not self._stop.is_set():
            self.bank.set_state(int(time.time()) % 32)
            self._sleep(1.0)

    def _game_outside_in(self):
        """Gioco 20: outside in — opposto di inside out, si comprime dai bordi al centro."""
        n   = len(self.bank._leds)
        mid = n // 2

        expand = []
        for r in range(mid + 1):
            mask = 0
            for i in range(mid - r, mid + r + 1):
                if 0 <= i < n:
                    mask |= (1 << i)
            expand.append(mask)

        sequenza = list(reversed(expand)) + expand[1:]   # pieno→centro→pieno

        while not self._stop.is_set():
            for mask in sequenza:
                if self._stop.is_set(): break
                self.bank.set_state(mask)
                self._sleep(0.15)

    def _game_zip(self):
        """Gioco 21: zip — due punti partono dai bordi opposti e si incrociano al centro."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            for step in range(n // 2 + 1):     # avvicinamento
                if self._stop.is_set(): break
                mask = (1 << step) | (1 << (n - 1 - step))
                self.bank.set_state(mask)
                self._sleep(0.12)
            for step in range(n // 2, -1, -1): # allontanamento
                if self._stop.is_set(): break
                mask = (1 << step) | (1 << (n - 1 - step))
                self.bank.set_state(mask)
                self._sleep(0.12)

    def _game_fireworks(self):
        """Gioco 22: fuochi d'artificio — esplosioni di luce che si espandono da un punto casuale."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            centro = random.randint(0, n - 1)
            for raggio in range(n):
                if self._stop.is_set(): break
                mask = 0
                for i in range(centro - raggio, centro + raggio + 1):
                    if 0 <= i < n:
                        mask |= (1 << i)
                self.bank.set_state(mask)
                self._sleep(0.07)
            self.bank.all_off()
            self._sleep(random.uniform(0.3, 0.7))

    def _game_morse_luce(self):
        """Gioco 23: scrive LUCE in codice Morse (tematico con il progetto)."""
        DIT = 0.2
        DAH = 0.6
        SEP = 0.2
        LET = 0.5
        WRD = 1.2

        MORSE = {
            'L': [DIT, DAH, DIT, DIT],
            'U': [DIT, DIT, DAH],
            'C': [DAH, DIT, DAH, DIT],
            'E': [DIT],
        }

        while not self._stop.is_set():
            for simboli in MORSE.values():
                for durata in simboli:
                    if self._stop.is_set(): break
                    self.bank.all_on();  self._sleep(durata)
                    self.bank.all_off(); self._sleep(SEP)
                self._sleep(LET)
            self._sleep(WRD)

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
    if not GPIO_AVAILABLE:
        print("[WARN] gpiozero non disponibile — modalità mock (nessun LED fisico)")
    server = ProtocolServer(HOST, PORT, LED_PINS)
    server.run()

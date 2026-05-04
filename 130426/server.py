"""Server TCP per gestire i LED e i giochi sul progetto LUCE.

Questo modulo espone un server TCP che accetta un protocollo a 1 byte.
I comandi ricevuti possono impostare direttamente lo stato dei LED oppure
avviare uno dei giochi di luce predefiniti.

Struttura principale:
 - LEDBank: gestisce un insieme di LED fisici tramite una bitmask
 - GameEngine: esegue pattern luminosi in un thread separato
 - ProtocolServer: accetta connessioni, decodifica comandi e li inoltra
"""

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

from protocol import Command, CommandType


# ============================================================
# CONFIGURAZIONE
# ============================================================

# Indirizzo e porta del server TCP. Il server ascolta su qualsiasi
# interfaccia di rete disponibile e accetta connessioni provenienti da
# altri dispositivi nella stessa rete locale.
HOST = "0.0.0.0"
PORT = 8888

# Mappatura dei 5 LED ai pin GPIO della Raspberry Pi.
# La bitmask del comando SET_STATE usa il bit i-esimo per controllare
# il LED con indice i.
LED_PINS = [17, 27, 22, 23, 24]


# ============================================================
# LED BANK — gestisce il banco di LED tramite bitmask
# ============================================================

class LEDBank:
    """Astrae un gruppo di LED fisici in un unico oggetto controllabile via bitmask."""

    def __init__(self, pins: list):
        # Crea istanze LED per tutti i pin specificati.
        self._leds = [LED(p) for p in pins]
        self._state = 0x00  # stato interno attuale dei LED, utile per eventuali risposte future

    def set_state(self, bitmask: int):
        """Imposta lo stato di tutti i LED in un colpo solo.

        Il bit N della bitmask controlla il LED N:
          - bit 1 -> LED acceso
          - bit 0 -> LED spento

        Anche se usiamo solo 5 LED, memorizziamo solo gli ultimi 8 bit per
        mantenere una semantica semplice con la bitmask.
        """
        self._state = bitmask & 0xFF

        # Itera attraverso i LED collegati e aggiorna ciascuno in base al bit corrispondente.
        for i, led in enumerate(self._leds):
            if bitmask & (1 << i):
                led.on()
            else:
                led.off()

    def get_state(self) -> int:
        """Restituisce la bitmask corrispondente allo stato corrente dei LED."""
        return self._state

    def all_off(self):
        """Spegne tutti i LED del banco."""
        self.set_state(0x00)

    def all_on(self):
        """Accende tutti i LED del banco."""
        self.set_state((1 << len(self._leds)) - 1)


# ============================================================
# GAME ENGINE — esegue i giochi di luce in un thread dedicato
# ============================================================

class GameEngine:
    """Gestisce i giochi di luce.

    Ogni gioco viene eseguito in un thread separato. Il thread legge
    periodicamente un evento di stop per verificare se deve terminare.
    """

    def __init__(self, bank: LEDBank):
        self.bank = bank
        self._thread = None
        self._stop = threading.Event()

        # Dizionario che associa un identificatore numerico al metodo del gioco.
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
        """Esegue una pausa interrompibile controllando l'evento di stop."""
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
            for i in range(n):
                if self._stop.is_set():
                    break
                self.bank.set_state((1 << (i + 1)) - 1)
                self._sleep(0.2)
            for i in range(n - 1, -1, -1):
                if self._stop.is_set():
                    break
                self.bank.set_state((1 << i) - 1)
                self._sleep(0.2)

    def _game_sos(self):
        """Gioco 7: segnale SOS in codice Morse con tutti i LED."""
        while not self._stop.is_set():
            for _ in range(3):
                if self._stop.is_set():
                    break
                self.bank.all_on(); self._sleep(0.2)
                self.bank.all_off(); self._sleep(0.2)
            for _ in range(3):
                if self._stop.is_set():
                    break
                self.bank.all_on(); self._sleep(0.6)
                self.bank.all_off(); self._sleep(0.2)
            for _ in range(3):
                if self._stop.is_set():
                    break
                self.bank.all_on(); self._sleep(0.2)
                self.bank.all_off(); self._sleep(0.2)
            self._sleep(1.0)

    def _game_heartbeat(self):
        """Gioco 8: doppio flash rapido seguito da una lunga pausa."""
        while not self._stop.is_set():
            self.bank.all_on(); self._sleep(0.08)
            self.bank.all_off(); self._sleep(0.12)
            self.bank.all_on(); self._sleep(0.08)
            self.bank.all_off(); self._sleep(0.8)

    def _game_inside_out(self):
        """Gioco 9: si espande dal centro verso i bordi e poi si ricomprime."""
        n = len(self.bank._leds)
        mid = n // 2

        expand = []
        for r in range(mid + 1):
            mask = 0
            for i in range(mid - r, mid + r + 1):
                if 0 <= i < n:
                    mask |= (1 << i)
            expand.append(mask)

        contract = list(reversed(expand))
        sequenza = expand + contract[1:]

        while not self._stop.is_set():
            for mask in sequenza:
                if self._stop.is_set():
                    break
                self.bank.set_state(mask)
                self._sleep(0.15)

    def _game_knight_rider(self):
        """Gioco 10: Knight Rider — scia di 2 LED che rimbalza avanti e indietro."""
        n = len(self.bank._leds)
        sequenza = list(range(n)) + list(range(n - 2, 0, -1))
        prev = None
        while not self._stop.is_set():
            for i in sequenza:
                if self._stop.is_set():
                    break
                mask = (1 << i) | (1 << prev if prev is not None else 0)
                self.bank.set_state(mask)
                prev = i
                self._sleep(0.08)

    def _game_police(self):
        """Gioco 11: luci della polizia — sinistra e destra lampeggiano in alternanza."""
        sinistra = 0b00011
        destra = 0b11000
        while not self._stop.is_set():
            for _ in range(3):
                if self._stop.is_set():
                    break
                self.bank.set_state(sinistra); self._sleep(0.08)
                self.bank.all_off(); self._sleep(0.05)
            for _ in range(3):
                if self._stop.is_set():
                    break
                self.bank.set_state(destra); self._sleep(0.08)
                self.bank.all_off(); self._sleep(0.05)
            self._sleep(0.2)

    def _game_strobe(self):
        """Gioco 12: strobo — blink velocissimo."""
        while not self._stop.is_set():
            self.bank.all_on(); self._sleep(0.04)
            self.bank.all_off(); self._sleep(0.04)

    def _game_snake(self):
        """Gioco 13: snake — punto luminoso con scia di 2 LED."""
        n = len(self.bank._leds)
        sequenza = list(range(n)) + list(range(n - 2, 0, -1))
        while not self._stop.is_set():
            for idx, i in enumerate(sequenza):
                if self._stop.is_set():
                    break
                mask = 1 << i
                if idx > 0:
                    mask |= 1 << sequenza[idx - 1]
                self.bank.set_state(mask)
                self._sleep(0.1)

    def _game_twinkle(self):
        """Gioco 14: twinkle — accende e spegne LED casuali in modo irregolare."""
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
            for i in range(n):
                if self._stop.is_set():
                    break
                mask |= (1 << i)
                self.bank.set_state(mask)
                self._sleep(0.15)
            for i in range(n):
                if self._stop.is_set():
                    break
                mask &= ~(1 << i)
                self.bank.set_state(mask)
                self._sleep(0.15)

    def _game_pairs(self):
        """Gioco 16: coppie — lampeggiano bordi, interni e centro a turno."""
        coppie = [0b10001, 0b01010, 0b00100]
        while not self._stop.is_set():
            for mask in coppie:
                if self._stop.is_set():
                    break
                self.bank.set_state(mask)
                self._sleep(0.35)
            self.bank.all_off()
            self._sleep(0.15)

    def _game_morse_ciao(self):
        """Gioco 17: scrive CIAO in codice Morse usando tutti i LED."""
        DIT = 0.2
        DAH = 0.6
        SEP = 0.2
        LET = 0.5
        WRD = 1.2

        MORSE = {
            'C': [DAH, DIT, DAH, DIT],
            'I': [DIT, DIT],
            'A': [DIT, DAH],
            'O': [DAH, DAH, DAH],
        }

        while not self._stop.is_set():
            for simboli in MORSE.values():
                for durata in simboli:
                    if self._stop.is_set():
                        break
                    self.bank.all_on(); self._sleep(durata)
                    self.bank.all_off(); self._sleep(SEP)
                self._sleep(LET)
            self._sleep(WRD)

    def _game_dice(self):
        """Gioco 18: dado — agitazione casuale e poi risultato da 1 a 5 LED."""
        n = len(self.bank._leds)
        max_val = (1 << n) - 1
        while not self._stop.is_set():
            for _ in range(12):
                if self._stop.is_set():
                    break
                self.bank.set_state(random.randint(1, max_val))
                self._sleep(0.07)
            if self._stop.is_set():
                break
            risultato = random.randint(1, n)
            self.bank.set_state((1 << risultato) - 1)
            self._sleep(2.0)

    def _game_binary_clock(self):
        """Gioco 19: orologio binario che mostra i secondi correnti mod 32."""
        while not self._stop.is_set():
            self.bank.set_state(int(time.time()) % 32)
            self._sleep(1.0)

    def _game_outside_in(self):
        """Gioco 20: opposite di inside_out, si comprime dai bordi al centro."""
        n = len(self.bank._leds)
        mid = n // 2

        expand = []
        for r in range(mid + 1):
            mask = 0
            for i in range(mid - r, mid + r + 1):
                if 0 <= i < n:
                    mask |= (1 << i)
            expand.append(mask)

        sequenza = list(reversed(expand)) + expand[1:]

        while not self._stop.is_set():
            for mask in sequenza:
                if self._stop.is_set():
                    break
                self.bank.set_state(mask)
                self._sleep(0.15)

    def _game_zip(self):
        """Gioco 21: zip — due punti si avvicinano e si allontanano al centro."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            for step in range(n // 2 + 1):
                if self._stop.is_set():
                    break
                mask = (1 << step) | (1 << (n - 1 - step))
                self.bank.set_state(mask)
                self._sleep(0.12)
            for step in range(n // 2, -1, -1):
                if self._stop.is_set():
                    break
                mask = (1 << step) | (1 << (n - 1 - step))
                self.bank.set_state(mask)
                self._sleep(0.12)

    def _game_fireworks(self):
        """Gioco 22: fuochi d'artificio — esplosione luminosa da un punto casuale."""
        n = len(self.bank._leds)
        while not self._stop.is_set():
            centro = random.randint(0, n - 1)
            for raggio in range(n):
                if self._stop.is_set():
                    break
                mask = 0
                for i in range(centro - raggio, centro + raggio + 1):
                    if 0 <= i < n:
                        mask |= (1 << i)
                self.bank.set_state(mask)
                self._sleep(0.07)
            self.bank.all_off()
            self._sleep(random.uniform(0.3, 0.7))

    def _game_morse_luce(self):
        """Gioco 23: scrive LUCE in codice Morse con tutti i LED."""
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
                    if self._stop.is_set():
                        break
                    self.bank.all_on(); self._sleep(durata)
                    self.bank.all_off(); self._sleep(SEP)
                self._sleep(LET)
            self._sleep(WRD)

    # --- Controllo ---

    def start(self, game_id: int):
        """Avvia un gioco specificato dall'identificatore game_id."""
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
        """Ferma il gioco in esecuzione e spegne tutti i LED."""
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join()
            self.bank.all_off()
            print("[GAME] gioco fermato")


# ============================================================
# PROTOCOL SERVER — accetta connessioni e fa il dispatch
# ============================================================

class ProtocolServer:
    """Server TCP che interpreta il protocollo a 1 byte e controlla LED e giochi."""

    def __init__(self, host: str, port: int, led_pins: list):
        self.host = host
        self.port = port
        self.bank = LEDBank(led_pins)
        self.engine = GameEngine(self.bank)

    def _dispatch(self, cmd: Command):
        """Esegue l'azione corrispondente al comando ricevuto."""
        if cmd.tipo == CommandType.SET_STATE:
            self.engine.stop()
            self.bank.set_state(cmd.valore)
            print(f"[SET_STATE] bitmask = {cmd.valore:05b}")

        elif cmd.tipo == CommandType.START_GAME:
            self.engine.start(cmd.valore)

    def _handle_client(self, conn: socket.socket, addr):
        """Gestisce la comunicazione con un singolo client."""
        print(f"[CONN] connesso: {addr}")

        try:
            while True:
                data = conn.recv(Command.SIZE)
                if not data:
                    break

                try:
                    cmd = Command.decode(data)
                    print(f"[RX] {cmd}")
                    self._dispatch(cmd)
                except ValueError as e:
                    print(f"[ERR] {e}")

        except ConnectionResetError:
            pass
        finally:
            conn.close()
            print(f"[CONN] disconnesso: {addr}")

    def run(self):
        """Avvia il server TCP e accetta connessioni in un loop infinito."""
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

# Idea 4 — Protocollo tipizzato a 2 byte

Comunicazione TCP tra un client (PC) e un server (Raspberry Pi) usando un protocollo binario
minimal: ogni messaggio è esattamente **2 byte** — il primo identifica il tipo di comando
(opcode), il secondo trasporta i dati (payload).

---

## Struttura del messaggio

```
Byte 0          Byte 1
┌──────────────┐ ┌──────────────┐
│    Opcode    │ │   Payload    │
└──────────────┘ └──────────────┘
  tipo comando      dati
```

### Tabella opcode

| Opcode | Nome        | Payload                  | Descrizione                         |
|--------|-------------|--------------------------|-------------------------------------|
| `0x01` | SET_STATE   | Bitmask LED (bit 0–4)    | Imposta lo stato di ciascun LED     |
| `0x02` | START_GAME  | ID gioco (0–255)         | Avvia un gioco di luce              |
| `0x03` | STOP_GAME   | Ignorato (`0x00`)        | Arresta il gioco in corso           |
| `0x04` | GET_STATE   | Ignorato (`0x00`)        | Richiede lo stato corrente          |

Solo `GET_STATE` genera una risposta: il server risponde con `SET_STATE` + bitmask attuale.

---

## Struttura dei file

```
130426/
├── protocol.py   # definizione del protocollo (opcode, Message, helper)
├── server.py     # server Raspberry Pi: gestisce LED e giochi
├── client.py     # client PC: invia comandi al server
└── README.md
```

### `protocol.py`

Contiene tutto ciò che è condiviso tra client e server:

- **`Opcode`** — enum con i 4 opcode definiti.
- **`Message`** — classe che rappresenta un messaggio:
  - `encode()` → serializza in 2 byte con `struct.pack`
  - `decode(data)` → deserializza 2 byte e solleva `ProtocolError` se malformati
- **Funzioni helper** — `msg_set_state`, `msg_start_game`, `msg_stop_game`, `msg_get_state`
  per costruire messaggi senza dover ricordare gli opcode a mano.

### `server.py`

Gira sul Raspberry Pi. Si compone di tre classi:

- **`LEDBank`** — controlla il banco di 5 LED tramite bitmask. Il bit N accende il LED N.
  Mantiene `_state` internamente per poter rispondere a `GET_STATE` senza leggere i GPIO.

- **`GameEngine`** — esegue i giochi in un thread separato usando `threading.Event`
  come "bandierina" di stop (stesso pattern di `160326/thread.py`).
  Il metodo `_sleep` è interrompibile: non aspetta il timeout se lo stop è richiesto.

  | ID | Gioco           | Descrizione                         |
  |----|-----------------|-------------------------------------|
  | 0  | Chase           | Luce che scorre da sinistra a destra|
  | 1  | Blink           | Tutti i LED lampeggiano insieme     |
  | 2  | Alternating     | Pattern 10101 / 01010 alternato     |
  | 3  | Binary count    | Conta in binario da 0 a 31          |

- **`ProtocolServer`** — server TCP che accetta più client in contemporanea
  (un thread per connessione). Il metodo `_dispatch` fa lo switch sull'opcode
  e chiama il metodo giusto su `LEDBank` o `GameEngine`.

### `client.py`

Gira sul PC. La classe **`ProtocolClient`** espone un'API ad alto livello:

```python
with ProtocolClient("192.168.5.55", 8888) as client:
    client.set_state(0b10101)   # LED 0, 2, 4 accesi
    client.start_game(1)        # avvia blink
    client.stop_game()
    state = client.get_state()  # legge stato dal server
```

Il context manager (`with`) garantisce che il socket venga sempre chiuso.

---

## Collegamento hardware (Raspberry Pi)

```
Raspberry Pi            Breadboard
─────────────           ──────────
GPIO 17  ──[220Ω]──── LED 0 (anodo) ──── GND
GPIO 27  ──[220Ω]──── LED 1 (anodo) ──── GND
GPIO 22  ──[220Ω]──── LED 2 (anodo) ──── GND
GPIO 23  ──[220Ω]──── LED 3 (anodo) ──── GND
GPIO 24  ──[220Ω]──── LED 4 (anodo) ──── GND
GND      ──────────── colonna GND
```

> Il valore da 220Ω è indicativo per LED standard a 3.3V / ~10mA.
> Il catodo (gamba corta) va a massa; l'anodo (gamba lunga) al pin GPIO tramite resistore.

---

## Come avviare

**Sul Raspberry Pi** (server):
```bash
python3 server.py
```

**Sul PC** (client):
```bash
python3 client.py
```

Modifica `SERVER_IP` in `client.py` con l'IP del Raspberry Pi sulla rete locale.

---

## Esempio di scambio

```
Client → Server:  0x01 0x15    SET_STATE,  bitmask 10101 → LED 0, 2, 4 accesi
Client → Server:  0x02 0x00    START_GAME, gioco 0 (chase)
Client → Server:  0x03 0x00    STOP_GAME
Client → Server:  0x04 0x00    GET_STATE
Server → Client:  0x01 0x15    risposta: stato corrente = LED 0, 2, 4 accesi
```

---

## Dipendenze

```bash
pip install gpiozero   # solo sul Raspberry Pi
```

Sul PC `gpiozero` non serve: `client.py` importa solo `protocol.py` e la libreria standard.

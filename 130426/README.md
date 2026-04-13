# Idea 4 — Protocollo tipizzato a 1 byte

Comunicazione TCP tra un client (PC) e un server (Raspberry Pi) usando un protocollo binario minimale: ogni comando e' esattamente **1 byte**.

Il tipo del comando viene inferito dal valore del byte:

- `0-31` -> `SET_STATE` (bitmask LED)
- `32-255` -> `START_GAME` (ID gioco = byte - 32)

Il protocollo e' unidirezionale: il server non invia risposte.

---

## Struttura del comando

```
Byte 0
┌──────────────┐
│   Command    │
└──────────────┘
```

### Mappatura byte

| Byte | Tipo comando | Payload logico |
|------|--------------|----------------|
| `0-31` | `SET_STATE` | Bitmask LED (bit 0-4) |
| `32-255` | `START_GAME` | `game_id = byte - 32` |

Costanti di riferimento (in `protocol.py`):

- `BITMASK_MAX = 31`
- `GAME_OFFSET = 32`
- `GAME_MAX_ID = 223`

---

## Struttura dei file

```
130426/
|-- protocol.py
|-- server.py
|-- client.py
|-- tests/
|   |-- test_protocol.py
|   `-- test_client_parse_bitmask.py
`-- README.md
```

### `protocol.py`

Contiene la logica condivisa tra client e server:

- `CommandType` (`SET_STATE`, `START_GAME`)
- `Command` con:
  - `encode()` -> serializza in 1 byte
  - `decode(data)` -> deserializza 1 byte e valida la lunghezza
- helper:
  - `cmd_set_state(bitmask)`
  - `cmd_start_game(game_id)`
  - `cmd_all_off()`

Validazione:

- bitmask valida: `0-31`
- game_id valido: `0-223`

### `server.py`

- `LEDBank`: controlla 5 LED tramite bitmask.
- `GameEngine`: esegue i giochi di luce in un thread dedicato (stop con `threading.Event`).
- `ProtocolServer`: riceve 1 byte, lo decodifica e fa dispatch:
  - `SET_STATE` -> ferma eventuale gioco e imposta lo stato LED
  - `START_GAME` -> avvia il gioco richiesto

Sono disponibili 24 giochi (`game_id` da 0 a 23).

### `client.py`

`ProtocolClient` espone API ad alto livello:

```python
with ProtocolClient("192.168.5.62", 8888) as client:
    client.set_state(0b10101)
    client.start_game(3)
    client.stop()
```

Include anche un menu interattivo e il parser `_parse_bitmask`, che accetta input:

- binario (`10101`)
- esadecimale (`0x15`)
- decimale (`21`)

---

## Collegamento hardware (Raspberry Pi)

```
GPIO 17  --[220ohm]-- LED 0 (anodo) -- GND
GPIO 27  --[220ohm]-- LED 1 (anodo) -- GND
GPIO 22  --[220ohm]-- LED 2 (anodo) -- GND
GPIO 23  --[220ohm]-- LED 3 (anodo) -- GND
GPIO 24  --[220ohm]-- LED 4 (anodo) -- GND
```

---

## Avvio

Server (su Raspberry Pi):

```bash
python3 server.py
```

Client (su PC):

```bash
python3 client.py
```

---

## Suite di test

Dalla cartella `130426`:

```bash
python3 -m unittest discover -s tests -v
```

Copertura attuale:

- validazione range in `cmd_set_state` e `cmd_start_game`
- codifica/decodifica di `Command`
- helper `cmd_all_off`
- parsing input utente in `_parse_bitmask`

---

## Dipendenze

```bash
pip install gpiozero
```

`gpiozero` serve solo sul Raspberry Pi. In ambiente PC il server usa una modalita' mock se la libreria non e' disponibile.

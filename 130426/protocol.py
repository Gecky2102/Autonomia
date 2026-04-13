from enum import Enum


# ============================================================
# SOGLIE DEL PROTOCOLLO
#
#   0–31   → bitmask di stato LED  (5 bit, copre fino a 5 LED)
#   32–255 → codice gioco di luce  (224 giochi disponibili)
#
#   Un solo byte: nessun campo "tipo" esplicito.
#   Il tipo si inferisce confrontando il valore con la soglia.
# ============================================================

BITMASK_MAX  = 31    # 0b11111 — valore massimo per una bitmask a 5 LED
GAME_OFFSET  = 32    # i codici gioco partono da qui
GAME_MAX_ID  = 255 - GAME_OFFSET   # 223 — massimo ID gioco supportato


class CommandType(Enum):
    SET_STATE  = "state"
    START_GAME = "game"


# ============================================================
# COMMAND — un singolo byte inviato dal client al server
# ============================================================

class Command:

    SIZE = 1   # il protocollo è a 1 byte fisso

    def __init__(self, tipo: CommandType, valore: int):
        self.tipo   = tipo
        self.valore = valore

    def encode(self) -> bytes:
        """Serializza il comando in 1 byte da inviare sul socket."""
        if self.tipo == CommandType.SET_STATE:
            return bytes([self.valore & BITMASK_MAX])
        else:
            return bytes([GAME_OFFSET + self.valore])

    @classmethod
    def decode(cls, data: bytes) -> 'Command':
        """Deserializza 1 byte in arrivo in un oggetto Command.

        La distinzione tra stato e gioco si basa sulla soglia:
          byte ≤ 31  → SET_STATE  (bitmask)
          byte ≥ 32  → START_GAME (game_id = byte - 32)
        """
        if len(data) != cls.SIZE:
            raise ValueError(f"Byte atteso: {cls.SIZE}, ricevuti: {len(data)}")

        byte_val = data[0]

        if byte_val <= BITMASK_MAX:
            return cls(CommandType.SET_STATE, byte_val)
        else:
            return cls(CommandType.START_GAME, byte_val - GAME_OFFSET)

    def __repr__(self):
        if self.tipo == CommandType.SET_STATE:
            return f"Command(SET_STATE, bitmask={self.valore:05b})"
        else:
            return f"Command(START_GAME, game_id={self.valore})"


# ============================================================
# HELPER — costruttori rapidi
# ============================================================

def cmd_set_state(bitmask: int) -> Command:
    """bitmask: bit 0–4 → LED 0–4  (es. 0b10101 → LED 0, 2, 4 accesi)."""
    if bitmask > BITMASK_MAX:
        raise ValueError(f"Bitmask {bitmask} fuori range (max {BITMASK_MAX})")
    return Command(CommandType.SET_STATE, bitmask)

def cmd_start_game(game_id: int) -> Command:
    """game_id: 0–223  →  byte inviato = game_id + 32."""
    if game_id > GAME_MAX_ID:
        raise ValueError(f"game_id {game_id} fuori range (max {GAME_MAX_ID})")
    return Command(CommandType.START_GAME, game_id)

def cmd_all_off() -> Command:
    """Spegne tutti i LED e ferma il gioco in corso (bitmask = 0)."""
    return Command(CommandType.SET_STATE, 0x00)

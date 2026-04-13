import struct
from enum import IntEnum


# ============================================================
# OPCODE — identifica il tipo di comando nel primo byte
# ============================================================

class Opcode(IntEnum):
    SET_STATE  = 0x01   # imposta i LED tramite bitmask
    START_GAME = 0x02   # avvia un gioco di luce
    STOP_GAME  = 0x03   # ferma il gioco in corso
    GET_STATE  = 0x04   # richiede lo stato corrente al server


# ============================================================
# ECCEZIONI
# ============================================================

class ProtocolError(Exception):
    """Sollevata quando un messaggio non rispetta il formato atteso."""
    pass


# ============================================================
# MESSAGGIO — unità atomica di comunicazione (2 byte fissi)
#
#   Byte 0: opcode  → tipo di comando
#   Byte 1: payload → dati associati al comando
# ============================================================

class Message:

    SIZE = 2  # dimensione fissa in byte, non cambia mai

    def __init__(self, opcode: Opcode, payload: int = 0x00):
        self.opcode  = opcode
        self.payload = payload & 0xFF  # il payload è sempre un singolo byte

    def encode(self) -> bytes:
        """Serializza il messaggio nei 2 byte da inviare sul socket."""
        return struct.pack('BB', int(self.opcode), self.payload)

    @classmethod
    def decode(cls, data: bytes) -> 'Message':
        """Deserializza 2 byte in arrivo dal socket in un oggetto Message.

        Solleva ProtocolError se i byte sono malformati o l'opcode è sconosciuto.
        """
        if len(data) != cls.SIZE:
            raise ProtocolError(
                f"Messaggio malformato: attesi {cls.SIZE} byte, ricevuti {len(data)}"
            )

        opcode_byte, payload = struct.unpack('BB', data)

        try:
            opcode = Opcode(opcode_byte)
        except ValueError:
            raise ProtocolError(f"Opcode sconosciuto: 0x{opcode_byte:02X}")

        return cls(opcode, payload)

    def __repr__(self):
        return f"Message({self.opcode.name}, payload=0x{self.payload:02X})"


# ============================================================
# HELPER — funzioni per costruire i messaggi comuni
# ============================================================

def msg_set_state(bitmask: int) -> Message:
    """Costruisce SET_STATE con la bitmask dei LED.

    Ogni bit corrisponde a un LED: bit 0 → LED 0, bit 4 → LED 4.
    Es: 0b10101 (0x15) → LED 0, 2, 4 accesi.
    """
    return Message(Opcode.SET_STATE, bitmask)

def msg_start_game(game_id: int) -> Message:
    """Costruisce START_GAME con l'ID del gioco (0–255)."""
    return Message(Opcode.START_GAME, game_id)

def msg_stop_game() -> Message:
    """Costruisce STOP_GAME. Il payload è ignorato dal server (convenzionalmente 0x00)."""
    return Message(Opcode.STOP_GAME, 0x00)

def msg_get_state() -> Message:
    """Costruisce GET_STATE. Il payload è ignorato dal server (convenzionalmente 0x00)."""
    return Message(Opcode.GET_STATE, 0x00)

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from protocol import (  # noqa: E402
    BITMASK_MAX,
    GAME_MAX_ID,
    GAME_OFFSET,
    Command,
    CommandType,
    cmd_all_off,
    cmd_set_state,
    cmd_start_game,
)


class TestProtocolHelpers(unittest.TestCase):
    def test_cmd_set_state_accepts_bounds(self):
        self.assertEqual(cmd_set_state(0).encode(), b"\x00")
        self.assertEqual(cmd_set_state(BITMASK_MAX).encode(), b"\x1f")

    def test_cmd_set_state_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            cmd_set_state(-1)
        with self.assertRaises(ValueError):
            cmd_set_state(BITMASK_MAX + 1)

    def test_cmd_start_game_accepts_bounds(self):
        self.assertEqual(cmd_start_game(0).encode(), bytes([GAME_OFFSET]))
        self.assertEqual(cmd_start_game(GAME_MAX_ID).encode(), b"\xff")

    def test_cmd_start_game_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            cmd_start_game(-1)
        with self.assertRaises(ValueError):
            cmd_start_game(GAME_MAX_ID + 1)

    def test_cmd_all_off(self):
        cmd = cmd_all_off()
        self.assertEqual(cmd.tipo, CommandType.SET_STATE)
        self.assertEqual(cmd.valore, 0)
        self.assertEqual(cmd.encode(), b"\x00")


class TestProtocolCodec(unittest.TestCase):
    def test_decode_set_state(self):
        cmd = Command.decode(b"\x15")
        self.assertEqual(cmd.tipo, CommandType.SET_STATE)
        self.assertEqual(cmd.valore, 0x15)

    def test_decode_start_game(self):
        cmd = Command.decode(b"\x20")
        self.assertEqual(cmd.tipo, CommandType.START_GAME)
        self.assertEqual(cmd.valore, 0)

        cmd = Command.decode(b"\xff")
        self.assertEqual(cmd.tipo, CommandType.START_GAME)
        self.assertEqual(cmd.valore, GAME_MAX_ID)

    def test_decode_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            Command.decode(b"")
        with self.assertRaises(ValueError):
            Command.decode(b"\x01\x02")


if __name__ == "__main__":
    unittest.main()

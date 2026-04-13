import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from client import _parse_bitmask  # noqa: E402


class TestParseBitmask(unittest.TestCase):
    def test_accepts_binary(self):
        self.assertEqual(_parse_bitmask("10101"), 21)
        self.assertEqual(_parse_bitmask("00011"), 3)

    def test_accepts_hex(self):
        self.assertEqual(_parse_bitmask("0x15"), 21)
        self.assertEqual(_parse_bitmask("0X1f"), 31)

    def test_accepts_decimal(self):
        self.assertEqual(_parse_bitmask("21"), 21)
        self.assertEqual(_parse_bitmask("  7  "), 7)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            _parse_bitmask("-1")
        with self.assertRaises(ValueError):
            _parse_bitmask("32")

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            _parse_bitmask("")
        with self.assertRaises(ValueError):
            _parse_bitmask("ciao")


if __name__ == "__main__":
    unittest.main()

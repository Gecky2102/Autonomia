import socket
import time

# ===== CONFIG =====
TARGET_IP = "192.168.5.55"
TARGET_PORT = 8888

PACKETS_PER_CYCLE = 1000000      # quanti pacchetti mandare
INTERVAL_SECONDS = 1        # ogni quanto tempo ripetere
MESSAGE = b"benchmark_test"

# ==================

print("PIN corretto. Avvio benchmark UDP...\n")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cycle = 0

while True:
    cycle += 1
    sent = 0

    for _ in range(PACKETS_PER_CYCLE):
        try:
            sock.sendto(MESSAGE, (TARGET_IP, TARGET_PORT))
            sent += 1
        except Exception as e:
            print("Errore invio:", e)

    print(f"Ciclo {cycle} - pacchetti inviati: {sent}")

    time.sleep(INTERVAL_SECONDS)
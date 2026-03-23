import socket
import struct
import time

SERVER_IP = "192.168.5.55"
SERVER_PORT = 8888

PAYLOAD_SIZE = 10000 * 1024   # 10KB
DELAY = 0.01               # pausa tra invii (10ms)

def benchmark():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))

    print(f"[CONNESSO] {SERVER_IP}:{SERVER_PORT}")

    payload = b"A" * PAYLOAD_SIZE
    header = struct.pack('!I', len(payload))
    packet = header + payload

    total_sent = 0
    start = time.time()

    try:
        while True:
            sock.sendall(packet)
            total_sent += len(packet)

            # statistiche ogni secondo
            elapsed = time.time() - start
            if elapsed >= 1:
                mb = total_sent / (1024 * 1024)
                print(f"[BENCH] inviati {mb:.2f} MB/s")
                total_sent = 0
                start = time.time()

            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n[STOP]")
    finally:
        sock.close()


if __name__ == "__main__":
    benchmark()
import socket
import struct
import time
from elec_price_monitor import config


def pico_test_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind(('127.0.0.1', config.UC_PORT))

    dest = ('127.0.0.1', config.PY_PORT)  # Match `device_loop`
    dest = ('10.10.10.178', config.PY_PORT)  # Match `device_loop`

    try:
        while True:
            print("\nChoose an option:")
            print("1 - send battery status")
            print("2 - send req. for time sync")
            print("3 - send req. for data")
            print("q - Quit")
            # choice = input("Enter option").strip()
            choice = '3'
            if choice == '1':
                # Send fake battery level msg: type=1, len=3, batt=42
                msg = struct.pack('>BHBB', config.MSG_TYPE_BATT_STATUS, 1, 0, 42)
                sock.sendto(msg, dest)
                print(f"Sent batt status to device_loop")
            elif choice == '2':
                # Send req. for time sync
                msg = struct.pack('>BHB', config.MSG_TYPE_TIME_SYNC, 0, 0)
                sock.sendto(msg, dest)
                print(f"Sent req for time sync to device_loop")
            elif choice == '3':
                msg = struct.pack('>BHB', config.MSG_TYPE_REQ_IMG_DATA, 0, 0)
                sock.sendto(msg, dest)
                print(f"Sent req for img data")
                break
            # Wait for data back
            sock.settimeout(5.0)
            try:
                data, _ = sock.recvfrom(1024)
                print(f"Got reply from device_loop: {data}")
            except socket.timeout:
                print("No reply received")

            time.sleep(5)

    except KeyboardInterrupt:
        print("Pico test server exiting")

if __name__ == '__main__':
    pico_test_server()
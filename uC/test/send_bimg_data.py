import socket
import time
import zlib # Import zlib for compression
import struct
#from .datadisk.elec_price_monitor.src.elec_price_monitor.local_comm.py import send_chunked_data
# Configuration for the Python script
PICO_IP = "10.10.10.221"  # Replace with your Pico's actual IP address
PICO_RX_PORT = 6667       # Port the Pico is listening on
PYTHON_LISTEN_PORT = 6666 # Port this Python script will listen on (Pico sends to this)
CHUNK_SIZE = 1400
MAX_SEQ_NUM = 5

def send_chunked_data(data, msg_type, send_sock:socket.socket, uC_addr:tuple[str, int]):

    total_len = len(data)
    if (total_len < CHUNK_SIZE):
        chunk_size = total_len
    else:
        chunk_size = CHUNK_SIZE

    if (total_len > CHUNK_SIZE* MAX_SEQ_NUM):
        print(f"There is going to be image data loss {total_len = } > {config.CHUNK_SIZE * config.MAX_SEQ_NUM}")

    seq_num = 0
    offset = 0
    while offset < total_len and seq_num < MAX_SEQ_NUM:
        chunk = data[offset: offset + chunk_size]
        payload_len = len(chunk)
        header = struct.pack('>BHB', msg_type, total_len, seq_num)
        packet = header + chunk
        sent = send_sock.sendto(packet, uC_addr)
        if sent != len(packet):
            print(f"Sent {sent} but packet length {len(packet)}")

        offset += payload_len
        seq_num += 1

    if (offset < total_len):
        print(f"Sent {offset = } but packet length {total_len = }, {seq_num = }")
    else:
        print(f"Sent {offset = } in {seq_num =} chunks")

#if __name__ == "__main__":
# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the listening port
sock.bind(('', PYTHON_LISTEN_PORT))
print(f"Python UDP server listening on port {PYTHON_LISTEN_PORT}")

sock.settimeout(1) # Set a timeout for receiving data

        # Send a compressed message from Python to Pico
original_message = f"Hello from Python! This is message number 1. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"This is some repetitive text to make compression effective. " \
                           f"The Pico should decompress this. Long live embedded systems!"
original_message = original_message*3        

        # Compress the message using zlib (default compression level)
compressed_message = zlib.compress(original_message.encode('utf-8'), 0)
sz = len(compressed_message)
print(sz)
send_chunked_data(compressed_message, 6, sock, (PICO_IP, PICO_RX_PORT))
#print(f"Sent compressed message ({len(compressed_message)} bytes) to Pico: '{original_message}'")
print(f"Sent compressed message ({len(compressed_message)} bytes) to Pico")


sock.close()


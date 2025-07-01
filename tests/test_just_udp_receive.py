import socket
import struct
import zlib
import config

# === CONFIG ===
UDP_IP = "0.0.0.0"      # Listen on all interfaces
UDP_PORT = config.UC_PORT        # Match this to sender
CHUNK_SIZE = config.CHUNK_SIZE       # Match sender
HEADER_SIZE = config.BASE_HDR_SIZE         # 1B type, 2B len, 2B seq

# === Buffers ===
buffers = {
    config.MSG_TYPE_RIMG_DATA: {},   # msg_type 1 = red_buf
    config.MSG_TYPE_BIMG_DATA: {},   # msg_type 2 = blk_buf
}

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Listening on {UDP_IP}:{UDP_PORT}")

    try:
        while True:
            data, addr = sock.recvfrom(2048)
            if len(data) < config.BASE_HDR_SIZE:
                print(f"Ignoring too-short packet from {addr}")
                continue
            print(f'len of data: {len(data) = }')
            msg_type = struct.unpack('>B', data[0])
            payload_len = struct.unpack('>H', data[1:2])
            seq_num = struct.unpack('>B', data[3])
            print(f"Got chunk: type={msg_type} seq={seq_num} len={payload_len} from {addr}")
            msg_type, payload_len, seq_num = struct.unpack('>BHB', data[:HEADER_SIZE])
            payload = data[HEADER_SIZE:]

            # print(f"Got {len(payload) = } total expected {payload_len =}")
            # if len(payload) != payload_len:
            #     print(f"Length mismatch! Got {len(payload)} expected {payload_len}")
            #     continue

            print(f"Got chunk: type={msg_type} seq={seq_num} len={payload_len} from {addr}")

            if msg_type not in buffers:
                print(f"Unknown msg_type {msg_type}, ignoring")
                continue

            buffers[msg_type][seq_num] = payload

            # --- For demonstration, assume single shot, reassemble when done ---
            # If you know how many chunks to expect, add logic here.
            # Here we fake it by reassembling when we get 5 chunks for demo.
            # if len(buffers[msg_type]) >= 2:
            #     reassemble(msg_type)

    except KeyboardInterrupt:
        print("Receiver shutting down.")
    finally:
        sock.close()


def reassemble(msg_type):
    # Reassemble chunks in order
    chunks = buffers[msg_type]
    data = b''.join(chunks[seq] for seq in sorted(chunks))
    print(f"Reassembled {len(data)} bytes for msg_type {msg_type}")

    # Decompress
    try:
        decompressed = zlib.decompress(data)
        print(f"Decompressed size: {len(decompressed)} bytes")
    except Exception as e:
        print(f"Decompression failed: {e}")

    # Clear buffer for next round
    buffers[msg_type] = {}


if __name__ == "__main__":
    main()
from .log import Log
from . import config
from datetime import datetime
import errno
import socket
import time
import struct

logger = Log.get_logger(__name__)
Log().change_log_level(__name__, Log.DEBUG)


def get_device_status() ->dict:
    logger.debug("Getting device status")
    now = datetime.now()

    device = {
        'batt': 0,
        'date': now.strftime("%d-%m-%Y")
    }
    return device
def handle_time_sync_msg(payload_len, payload):
    logger.debug(f"Received time sync message")
    if payload_len != config.MSG_TIME_SYNC_LEN:
        logger.warning(f"time sync msg not correct size {payload_len =}")

    pass

def handle_req_img_data(payload_len, payload, latest_red_buf, latest_blk_buf, send_sock, uC_addr):
    logger.debug(f"Received img req message")
    if payload_len != config.MSG_REQ_IMG_LEN:
        logger.warning(f"img req msg not correct size {payload_len =}")

    send_img_data(latest_red_buf, latest_blk_buf, send_sock, uC_addr)


def handle_battery_msg(payload_len, payload, status_queue):
    if payload_len != config.MSG_BATT_LEN:
        logger.warning(f"Battery msg not correct size {payload_len =}")

        # batt_level = struct.unpack('B', data[2:3])[0]
    batt_level = struct.unpack(config.BATT_STATUS_FORMAT, payload)[0]
                               # latest_data[config.MSG_BATT_OFFSET:
                               #             config.MSG_BATT_OFFSET + config.BATT_STATUS_SIZE])[0]
    logger.info(f"Received battery status: {batt_level}%")
    status_queue.put({'batt': batt_level})

def safe_sendto (sock:socket.socket, addr: tuple[str, int], data:bytes, retries:int=1):
    attempts = 0
    sent = 0
    while attempts < retries:
        try:
            sent = sock.sendto(data, addr)
            return sent
        except socket.error as e:
            if e.errno == errno.EINTR:
                attempts += 1
                time.sleep(0.1)
                logger.info(f"Socket sendto interrupted, retrying: {e}")
                continue
            else:
                logger.error(f"Socket error: {e}")
                break
    return sent

def send_chunked_data(data, msg_type, send_sock:socket.socket, uC_addr:tuple[str, int]):

    total_len = len(data)
    if (total_len < config.CHUNK_SIZE):
        chunk_size = total_len
    else:
        chunk_size = config.CHUNK_SIZE

    if (total_len > config.CHUNK_SIZE* config.MAX_SEQ_NUM):
        logger.error(f"There is going to be image data loss {total_len = } > {config.CHUNK_SIZE * config.MAX_SEQ_NUM}")

    seq_num = 0
    offset = 0
    while offset < total_len and seq_num < config.MAX_SEQ_NUM:
        chunk = data[offset: offset + chunk_size]
        payload_len = len(chunk)
        header = struct.pack('>BHB', msg_type, total_len, seq_num)
        packet = header + chunk
        sent = safe_sendto(send_sock, uC_addr, packet)
        if sent != len(packet):
            logger.warning(f"Sent {sent} but packet length {len(packet)}")

        offset += payload_len
        seq_num += 1

    if (offset < total_len):
        logger.error(f"Sent {offset = } but packet length {total_len = }, {seq_num = }")
    else:
        logger.info(f"Sent {offset = } in {seq_num =} chunks")
def send_img_data(latest_red_buf, latest_blk_buf, send_sock:socket.socket, uC_addr:tuple[str, int]):
    # payload = struct.pack('BB', config.MSG_TYPE_RIMG_DATA, 1 + len(latest_red_buf)) + struct.pack('II', len(latest_red_buf), len(latest_blk_buf))
    # send_sock.sendto(payload, uC_addr)
    # payload = struct.pack('BB', config.MSG_TYPE_RIMG_DATA, 1 + len(latest_red_buf)) + bytes(latest_red_buf)
    # safe_sendto(send_sock, uC_addr, payload)
    data = latest_red_buf
    msg_type = config.MSG_TYPE_RIMG_DATA
    send_chunked_data(data, msg_type, send_sock, uC_addr)
    data = latest_blk_buf
    msg_type = config.MSG_TYPE_BIMG_DATA
    send_chunked_data(data, msg_type, send_sock, uC_addr)


def device_loop(stop_event, status_queue, img_data_queue):
    # Create UDP socket
    try:
        rcv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rcv_sock.bind(('0.0.0.0', config.PY_PORT))  # Listen on all interfaces
        rcv_sock.settimeout(1.0)  # Set timeout for receiving data

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        uC_addr = (config.UC_IP, config.UC_PORT)  # Change to Pico IP and port
    except Exception as e:
        logger.error(f'Failed to open/bind sockets: {e}. Terminating {__name__} thread')
        return

    logger.info(f'{__name__} Started, opened udp port {config.PY_PORT}')

    latest_red_buf = latest_blk_buf = None
    latest_data = None
    while not stop_event.is_set():
        try:
            # start of loop
            # while True:
            try:
                data, addr = rcv_sock.recvfrom(1024)
                latest_data = data
            except socket.timeout:
                latest_data = None
                pass#break  # Normal — check for stop_event and keep looping

            if latest_data:
                if len(latest_data) < 2:
                    logger.warning(f"Ignoring short packet: {latest_data}")
                    latest_data = None
                    continue

                # msg_type, msg_len = struct.unpack('BB', data[:2])
                logger.debug(f"received {len(latest_data)=}, {config.BASE_HDR_FORMAT}, {config.BASE_HDR_SIZE}")
                msg_type, msg_len, seq_num = struct.unpack(config.BASE_HDR_FORMAT, latest_data[:config.BASE_HDR_SIZE])#unpack always returns a tuple
                if len(latest_data) != (msg_len + config.BASE_HDR_SIZE):
                    logger.warning(f"Bad length: expected {msg_len + config.BASE_HDR_SIZE}, got {len(latest_data)}")
                    continue

                payload_len = msg_len
                payload = latest_data[config.BASE_HDR_SIZE:]

                if msg_type == config.MSG_TYPE_BATT_STATUS:
                    handle_battery_msg(payload_len, payload, status_queue)
                elif msg_type == config.MSG_TYPE_TIME_SYNC:
                    handle_time_sync_msg(payload_len, payload)
                elif msg_type == config.MSG_TYPE_REQ_IMG_DATA:
                    handle_req_img_data(payload_len, payload, latest_red_buf, latest_blk_buf, send_sock, uC_addr)
                else:
                    logger.warning(f"Unknown msg_type: {msg_type}")

            # latest_data = None


                # Check if there’s new image data to send
            if not img_data_queue.empty():
                latest_red_buf, latest_blk_buf = img_data_queue.get()
                logger.info(f"Got new data on the img queue, sending image buffers to Pico")
                send_img_data(latest_red_buf, latest_blk_buf, send_sock, uC_addr)

            # Sleep functionality
            sleep_duration =1
            # logger.debug(f'Going to sleep: {sleep_duration = }')
            for _ in range(
                    sleep_duration):  # this is very bad way of sleeping, sleep for a second and check if main called u to exit.
                time.sleep(1)
                if stop_event.is_set():
                    return
            pass
        except Exception as e:
            logger.error(f'Exception handled:{e}')

    logger.debug(f'Called to terminate, stopping thread {__name__}')


'''
#pragma pack(push, 1)

#pragma pack(pop)
uint8_t payload_len = 8;  // bytes
uint8_t total_len = 2 + payload_len;

struct Message *msg = malloc(total_len);
msg->msg_type = 1;  // For example
msg->len = total_len;
memcpy(msg->data, your_payload, payload_len);
'''
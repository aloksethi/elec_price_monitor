import struct

APP_NAME = "elec_price_monitor"
DEBUG = True
MOCK_REST_DATA = False
DUMP_IMG_BUFF = False

SLEEP_DUR_NO_DATA: int = 5
SLEEP_DUR_NO_TMRW_DATA: int = 30 * 60
SLEEP_DUR_DATA_AVLBL: int = 2 * 60 * 60

if DEBUG and MOCK_REST_DATA:
    BASE_URL = "http://localhost:5000/api"
else:
    BASE_URL = "https://web-api.tp.entsoe.eu/api"

PY_PORT = 6666  #udp port for the server running at python
UC_PORT = 6667  #udp port for the server running at uC
UC_IP = "127.0.0.1"
CHUNK_SIZE = 1400 #1400 bytes in one udp packet, image size of one channel is uncompressed 38K n 2K compressed.
MAX_SEQ_NUM = 5
"""
base header, 
typedef struct Message __attribute__((packed)){
    uint8_t msg_type;  // What type of message (e.g., 1 = status, 2 = ack, etc.)
    uint16_t msg_len;   // Total length of the WHOLE message in bytes, including msg_type + len + payload
    uint8_t seq_num;   // Sequence number, usefule in case of chunked transmission
    uint8_t data[];    // Payload (variable length)
} msg_type;

"""

# Offsets and lengths — NO MAGIC NUMBERS
MSG_TYPE_OFFSET = 0
MSG_TYPE_LEN = 1
MSG_LEN_OFFSET = 1
MSG_LEN_LEN = 2

BASE_HDR_FORMAT = ">BHB"  # 4 bytes uint8_t, uint16_t, uint8_t
BASE_HDR_SIZE = struct.calcsize(BASE_HDR_FORMAT)

MSG_BATT_OFFSET = BASE_HDR_SIZE  #data returned from the pico
MSG_BATT_LEN = (1 + BASE_HDR_SIZE)
BATT_STATUS_FORMAT = "B"  # 1 byte:
# BATT_STATUS_SIZE = struct.calcsize(BATT_STATUS_FORMAT)

MSG_TIME_SYNC_OFFSET = BASE_HDR_SIZE
MSG_TIME_SYNC_LEN = BASE_HDR_SIZE #if pico sends this, then there is no data
MSG_REQ_IMG_OFFSET = BASE_HDR_SIZE
MSG_REQ_IMG_LEN = BASE_HDR_SIZE
MSG_SLEEP_DUR_LEN = BASE_HDR_SIZE

MSG_TYPE_BATT_STATUS = 1 	#pico sends, contains battery status
MSG_TYPE_TIME_SYNC = 2    	#if pico sends, contains no data, python replies with current time
MSG_TYPE_REQ_RIMG_DATA = 3   	#pico sends to request Red iamge data.
MSG_TYPE_REQ_BIMG_DATA = 4   	#pico sends to request Black iamge data.
MSG_TYPE_RIMG_DATA = 5      	#python sends with red channel data
MSG_TYPE_BIMG_DATA = 6      	#python sends with blacj channel data
MSG_TYPE_SLEEP_DUR = 7      	#python sends to tell pico to sleep for this many seconds, max 3600 seconds


def update_from_args(args):
    global DEBUG, DUMP_IMG_BUFF, PY_PORT, UC_PORT, UC_IP
    if args.debug is not None:
        DEBUG = args.debug
    if args.dump_img_buf is not None:
        DUMP_IMG_BUFF = args.debug
    if args.py_port is not None:
        PY_PORT = args.py_port
    if args.uc_port is not None:
        UC_PORT = args.uc_port
    if args.uc_ip is not None:
        UC_IP = args.uc_ip

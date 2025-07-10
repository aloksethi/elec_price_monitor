#ifndef __CONFIG_H_
#define __CONFIG_H_

#include <stdio.h>
#include <stdint.h>

/* FreeRTOS tasks priorities n stack sizes */
#define STACK_SIZE_UDP_TASK		(configSTACK_DEPTH_TYPE)1024 /*this value is in words not bytes*/
#define STACK_SIZE_EPAPER_TASK		(configSTACK_DEPTH_TYPE)1024 /*this value is in words not bytes*/
#define STACK_SIZE_CY43_TASK		(configSTACK_DEPTH_TYPE)512 /*this value is in words not bytes*/
#define STACK_SIZE_BLINK_TASK		(configMINIMAL_STACK_SIZE)

#define	PRIO_UDP_TASK			(tskIDLE_PRIORITY + 3UL)	
#define	PRIO_EPAPER_TASK		(tskIDLE_PRIORITY + 4UL)	
#define PRIO_CY43_TASK			(tskIDLE_PRIORITY + 2UL)
#define PRIO_BLINK_TASK			(tskIDLE_PRIORITY + 1UL)

// defines from config.py
#define UC_PORT		6667
#define PY_PORT		6666
// should have used the ip reassembly instead of chunking
#define CHUNK_SIZE	1400
#define MAX_SEQ_NUM	5

#define PYTHON_IP_ADD	"127.0.0.1"


#define MSG_TYPE_BATT_STATUS 	1 	//pico sends, contains battery status
#define MSG_TYPE_TIME_SYNC  	2    	//if pico sends, contains no data, python replies with current time
#define MSG_TYPE_REQ_IMG_DATA	3   	//pico sends to request iamge data. is requested only when pico reboots
#define MSG_TYPE_RIMG_DATA	4      	//python sends with red channel data
#define MSG_TYPE_BIMG_DATA	5      	//python sends with blacj channel data
#define MSG_TYPE_SLEEP_DUR	6      	//python sends to tell pico to sleep for this many seconds, max 3600 seconds

typedef struct UDP_Message 
{
    uint8_t msg_type;  // What type of message (e.g., 1 = status, 2 = ack, etc.)
    uint16_t msg_len;   // Total length of the WHOLE message in bytes
    uint8_t seq_num;   // Sequence number, usefule in case of chunked transmission
    uint8_t data[];    // Payload (variable length)
} __attribute__((__packed__)) udp_msg_t;




#endif

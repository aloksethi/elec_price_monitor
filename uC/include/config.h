#ifndef __CONFIG_H_
#define __CONFIG_H_

#include <stdio.h>
#include <stdint.h>

/* FreeRTOS tasks priorities n stack sizes */
#define STACK_SIZE_UDP_TASK		(configSTACK_DEPTH_TYPE)1024 /*this value is in words not bytes*/
#define STACK_SIZE_EPAPER_TASK	(configSTACK_DEPTH_TYPE)1024 /*this value is in words not bytes*/
#define STACK_SIZE_CY43_TASK	(configSTACK_DEPTH_TYPE)512 /*this value is in words not bytes*/
//#define STACK_SIZE_BLINK_TASK	(configMINIMAL_STACK_SIZE)

#define	PRIO_UDP_TASK			(tskIDLE_PRIORITY + 3UL)	
#define	PRIO_EPAPER_TASK		(tskIDLE_PRIORITY + 4UL)	
#define PRIO_CY43_TASK			(tskIDLE_PRIORITY + 2UL)
//#define PRIO_BLINK_TASK			(tskIDLE_PRIORITY + 1UL)



// defines from config.py
#define UC_PORT		            6667
#define PY_PORT		            6666
// should have used the ip reassembly instead of chunking
#define CHUNK_SIZE	            1400
#define MAX_SEQ_NUM	            4
#define DISP_BUFF_SIZE	        (648*480/8) /*used for allocating memory for decompression buffer*/
#define MAX_MSG_SIZE            (CHUNK_SIZE * MAX_SEQ_NUM) /*for allocating max size for udp reassembly*/
#define MAX_DATA_BUFS	        2   /*number of reassemlbed buffers for udp processing. equal to the udp queue length*/
#define MAX_UDP_EPAPER_QUEUE    1   /*writing only one buffer at a time*/

//#define PYTHON_IP_ADD	        "10.10.10.178"
#define PYTHON_IP_ADD	        "10.10.10.230" /*tux ip */

#define MSG_TYPE_BATT_STATUS 	1 	//pico sends, contains battery status
#define MSG_TYPE_TIME_SYNC  	2    	//if pico sends, contains no data, python replies with current time
#define MSG_TYPE_REQ_RIMG_DATA	3   	//pico sends to request Red iamge data.
#define MSG_TYPE_REQ_BIMG_DATA	4   	//pico sends to request Black iamge data.
#define MSG_TYPE_RIMG_DATA	    5      	//python sends with red channel data
#define MSG_TYPE_BIMG_DATA	    6      	//python sends with blacj channel data
#define MSG_TYPE_SLEEP_DUR	    7      	//python sends to tell pico to sleep for this many seconds, max 3600 seconds

typedef struct UDP_Message 
{
    uint8_t msg_type;  // What type of message (e.g., 1 = status, 2 = ack, etc.)
    uint16_t msg_len;   // Total length of the WHOLE message in bytes
    uint8_t seq_num;   // Sequence number, usefule in case of chunked transmission
    uint8_t data[];    // Payload (variable length)//flexible array member
} __attribute__((__packed__)) udp_msg_t;


typedef struct
{
    uint8_t msg_type;   // What type of message (e.g., 1 = status, 2 = ack, etc.)
    uint8_t idx;        // index to the reassembly_buff
    uint16_t msg_len;   // not very useful right now
//    uint8_t data[];    // Payload (variable length)
} __attribute__((__packed__)) udp_qmsg_t;


// PICO HW related
#define PICO_FIRST_ADC_PIN      26
#define PICO_POWER_SAMPLE_COUNT 3
#define PICO_WAKEUP_GPIO        2

#define UDP_CHUNK_TIMEOUT_MS    10000
#endif

#include <string.h>
#include "FreeRTOS.h"
#include "task.h"

#include "lwip/udp.h"
#include "lwip/ip_addr.h"
#include "lwip/pbuf.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/timeouts.h"

#include "config.h"
#define MAX_MSG_SIZE (CHUNK_SIZE * MAX_SEQ_NUM)
uint8_t reassembly_buff[MAX_MSG_SIZE];

static void udp_rx_callback(void *arg, struct udp_pcb *pcb, struct pbuf *p, const ip_addr_t *addr, u16_t port) 
{
	uint16_t cur_msg_len, expected_len;
	uint8_t cur_seq_num;
	udp_msg_t * msg_p;
	uint16_t chunk_len; // length of this datagram's payload
	uint16_t expected_msg_len = 0;
	static uint8_t expected_seq_num = 0;
	static uint16_t reassembly_len = 0;

	if (!p) return;
	if (p->len < sizeof(udp_msg_t)) {
		printf("Received too small pbuf\n");
		pbuf_free(p);
		return;
	}

	msg_p = (udp_msg_t *)p->payload;

	chunk_len = p->len; // Total length of this datagram's payload
	expected_msg_len = ntohs(msg_p->msg_len);


	// Simple sequence number check for reassembly
	if (msg_p->seq_num == expected_seq_num) 
	{
		// If this is the first chunk, reset the reassembly buffer
		if (msg_p->seq_num == 0) {
			reassembly_len = 0;
			printf("Receiving new message...\n");
		}

		uint16_t payload_len = chunk_len - offsetof(udp_msg_t, data);

		// Ensure we don't overflow the reassembly buffer
		if ((reassembly_len + payload_len) > MAX_MSG_SIZE) {
			printf("Error: Message too large for reassembly buffer. Discarding.\n");
			reassembly_len = 0;
			expected_seq_num = 0;
			pbuf_free(p);
			return;
		}

		// Copy just the data payload from the chunk into our main buffer
		memcpy(reassembly_buff + reassembly_len, msg_p->data, payload_len);
		reassembly_len += payload_len;

		// The msg_p->msg_len should contain the total length of the FINAL assembled message.
		// We check if we have received all the data for the full message.
		if (reassembly_len >= expected_msg_len)// - offsetof(msg_t, data))) 
		{
			printf("Full message reassembled. Total payload length: %d\n", reassembly_len);

//			decompress_message(reassembly_buffer, reassembly_len);

			// Reset for the next message
			reassembly_len = 0;
			expected_seq_num = 0;
		} else {
			// We are expecting more chunks
			printf("expecting more chunks, reassmebly_len=%d, msg_len=%d\n",reassembly_len, expected_msg_len);
			expected_seq_num++;
		}

	} else {
		// Handle out-of-order or lost packet
		printf("Unexpected sequence number. Expected: %d, Got: %d. Discarding message.\n", expected_seq_num, msg_p->seq_num);
		reassembly_len = 0;
		expected_seq_num = 0;
	}

	// Free the pbuf for this chunk
	pbuf_free(p);


}



void udp_task(void *params) {
    struct udp_pcb *pcb = udp_new();
    if (!pcb) {
        printf("Failed to create UDP PCB\n");
        vTaskDelete(NULL);
    }

    udp_bind(pcb, IP_ADDR_ANY, UC_PORT);
    udp_recv(pcb, udp_rx_callback, NULL);

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000)); // Nothing to do, LWIP runs in background
    }
}


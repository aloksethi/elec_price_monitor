#include <string.h>
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "event_groups.h"

#include "lwip/udp.h"
#include "lwip/ip_addr.h"
#include "lwip/pbuf.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/timeouts.h"

#include "config.h"
#include "miniz.h"

#define UDP_DATA_RECEIVED_BIT (1UL << 0UL) // Bit 0: Set when UDP data arrives
#define UDP_TIMER_FIRED_BIT   (1UL << 1UL) // Bit 1: Set when the periodic timer fires

#define MAX_MSG_SIZE (CHUNK_SIZE * MAX_SEQ_NUM)
#define MAX_DATA_BUFS	2
uint8_t g_empty_idx = 0;
uint8_t reassembly_buff[MAX_DATA_BUFS][MAX_MSG_SIZE];
static QueueHandle_t g_udp_rx_queue;
static EventGroupHandle_t g_udp_evnt_grp;

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

	msg_p = (udp_msg_t *)p->payload; // get the header
	expected_msg_len = ntohs(msg_p->msg_len);

	chunk_len = p->tot_len; // Total length of this datagram's payload. it can contain a chain of pbuffs so need to copy into a contiguous buffer

	// Simple sequence number check for reassembly
	if (msg_p->seq_num == expected_seq_num) 
	{
		uint16_t payload_len = chunk_len - offsetof(udp_msg_t, data);
		uint8_t *p_src, *p_dst, *p_contiguous_data;
		uint16_t tmp;

		// If this is the first chunk, reset the reassembly buffer
		if (msg_p->seq_num == 0) {
			reassembly_len = 0;
			printf("Receiving new message, idx:%d\n", g_empty_idx);
		}


		// Ensure we don't overflow the reassembly buffer
		if ((reassembly_len + payload_len) > MAX_MSG_SIZE) {
			printf("Error: Message too large for reassembly buffer. Discarding.\n");
			reassembly_len = 0;
			expected_seq_num = 0;
			pbuf_free(p);
			return;
		}

		p_contiguous_data = (uint8_t *)malloc(chunk_len);
		if (p_contiguous_data == NULL) {
			printf("ERROR: Failed to allocate memory for contiguous UDP data. Dropping packet.\n");
			pbuf_free(p); // Free the original pbuf chain
			return;
		}
		// Copy just the data payload from the chunk into our main buffer
		//memcpy(reassembly_buff[g_empty_idx] + reassembly_len, msg_p->data, payload_len);
		//tmp = pbuf_copy_partial(p, &reassembly_buff[g_empty_idx][0] + reassembly_len, chunk_len, 0);
		tmp = pbuf_copy_partial(p, p_contiguous_data, chunk_len, 0);
		if (tmp != chunk_len)
			printf("pbuf_copy didnt compelte\n");
		// contiguous_data will contain the udp_msg_t, so copy after it only
		p_src = p_contiguous_data + offsetof(udp_msg_t, data);
		p_dst = reassembly_buff[g_empty_idx] + reassembly_len;
		//memcpy(reassembly_buff[g_empty_idx] + reassembly_len, contiguous_data+offsetof(udp_msg_t, data), payload_len);
		memcpy(p_dst, p_src, payload_len);
		free(p_contiguous_data);

		reassembly_len += payload_len;

		// The msg_p->msg_len should contain the total length of the FINAL assembled message.
		// We check if we have received all the data for the full message.
		if (reassembly_len >= expected_msg_len)// - offsetof(msg_t, data))) 
		{
			BaseType_t xHigherPriorityTaskWoken;
			printf("Full message reassembled. Total payload length: %d\n", reassembly_len);
			// Reset for the next message
			reassembly_len = 0;
			expected_seq_num = 0;
			if (xQueueSendFromISR(g_udp_rx_queue, &g_empty_idx, &xHigherPriorityTaskWoken) == pdPASS) 
			{
				// If successfully sent to queue, signal the udp_task that data is available.
				g_empty_idx = (g_empty_idx + 1)%MAX_DATA_BUFS;
				xEventGroupSetBitsFromISR(g_udp_evnt_grp, UDP_DATA_RECEIVED_BIT, &xHigherPriorityTaskWoken);
			} 
			else 
			{
				// Queue was full, so we must free the pbuf here to prevent memory leaks.
				printf("UDP RX Queue full, dropping packet from %s:%d.\n", ipaddr_ntoa(addr), port);
			}
		} 
		else 
		{
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

	return;
}

#define DISP_BUFF_SIZE	(648*480/8)
uint8_t disp_buf[DISP_BUFF_SIZE];
 // --- Decompression Resources (Static Allocation for Stack Efficiency) ---
    // Allocate the decompressor state struct statically. This is the key to reducing stack usage.
    // Its large internal tables will now be in BSS/data memory, not on the task's stack.
static tinfl_decompressor decomp;

    // Define a maximum expected decompressed payload size.
    // UDP packets are typically limited to ~1472 bytes payload to avoid IP fragmentation.
    // If your compression ratio is 1:4, a 1472-byte compressed payload could be ~5.8KB decompressed.
    // Adjust this based on your actual expected maximum decompressed size.
    // A value of 4096 bytes (4KB) is a common starting point for small payloads.
#define MAX_DECOMPRESSED_PAYLOAD_SIZE 4096
static uint8_t decompressed_output_buffer[MAX_DECOMPRESSED_PAYLOAD_SIZE];
void deinflate_payload(uint8_t rx_msg)
{
	size_t in_buf_size = MAX_MSG_SIZE;//rx_msg.len;
	size_t out_buf_size = MAX_DECOMPRESSED_PAYLOAD_SIZE; 
	// Initialize the decompressor for each new decompression operation.
	tinfl_init(&decomp);

	// Assuming the payload is a Zlib compressed stream.
	// If it's raw Deflate, remove TINFL_FLAG_PARSE_ZLIB_HEADER.
	// If it's Gzip, use TINFL_FLAG_PARSE_GZIP_HEADER.
	// TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF is important as our output buffer is fixed.
	int inflate_flags = TINFL_FLAG_PARSE_ZLIB_HEADER | TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF;

	void *pSrc_buf = (void *)(&reassembly_buff[rx_msg][0]); // Input buffer (from pbuf)
	tinfl_status status = tinfl_decompress(
			&decomp,                   // Static decompressor state
			(const mz_uint8*)pSrc_buf, // Input buffer (contiguous)
			&in_buf_size,              // Input size (will be updated by tinfl)
			disp_buf, // Static output buffer
			disp_buf, // Static output buffer
			&out_buf_size,             // Output buffer capacity (will be updated by tinfl)
			inflate_flags
			);

	if (status == TINFL_STATUS_DONE) {
		printf("INFO: Successfully decompressed to %d bytes.\n",
				(int)out_buf_size); // out_buf_size now holds actual decompressed length

	} else if (status == TINFL_STATUS_HAS_MORE_OUTPUT) {
		printf("ERROR: Decompression failed: Output buffer too small \n");
		// This indicates MAX_DECOMPRESSED_PAYLOAD_SIZE needs to be increased.
	} else {
		printf("ERROR: Decompression failed with status %d \n",
				status);
	}
}

void udp_task(void *params) {
    struct udp_pcb *pcb = udp_new();
    if (!pcb) {
        printf("Failed to create UDP PCB\n");
        vTaskDelete(NULL);
    }

    udp_bind(pcb, IP_ADDR_ANY, UC_PORT);
    udp_recv(pcb, udp_rx_callback, NULL);

    g_udp_evnt_grp = xEventGroupCreate();
    if (g_udp_evnt_grp == NULL) {
        printf("FATAL: Failed to create UDP Event Group. Cannot start task.\n");
        return;
    }
    g_udp_rx_queue = xQueueCreate(MAX_DATA_BUFS, sizeof(g_empty_idx));
    if (g_udp_rx_queue == NULL)
    {
	    printf("failed to create udp rx queue\n");
	    return;
    }
    while (1) {
	    EventBits_t uxBits;
        uint8_t rx_msg;

        // Wait indefinitely for either the UDP_DATA_RECEIVED_BIT or UDP_TIMER_FIRED_BIT to be set.
        // pdTRUE: Clear the bits in the event group after reading them.
        // pdFALSE: Wait for ANY of the specified bits, not ALL.
        // portMAX_DELAY: Wait indefinitely until one of the bits is set.
        uxBits = xEventGroupWaitBits(g_udp_evnt_grp, UDP_DATA_RECEIVED_BIT | UDP_TIMER_FIRED_BIT,
				            pdTRUE,  // Clear bits on exit
				            pdFALSE, // Wait for any bit
				            portMAX_DELAY // Wait indefinitely
        				);

	if ((uxBits & UDP_DATA_RECEIVED_BIT) != 0) 
	{
		// Retrieve all available messages from the queue.
		// Loop until the queue is empty (xQueueReceive returns pdFAIL).
		while (xQueueReceive(g_udp_rx_queue, &rx_msg, 0) == pdPASS) 
		{ 
			printf("INFO: Received, queue index:%d\n", rx_msg);

			// --- Decompression using miniz_tinfl ---
			size_t decompressed_len = 0;
			// Assuming the payload is a Zlib compressed stream.
			// If it's raw Deflate, remove TINFL_FLAG_PARSE_ZLIB_HEADER.
			// If it's Gzip, use TINFL_FLAG_PARSE_GZIP_HEADER.
			int inflate_flags = TINFL_FLAG_PARSE_ZLIB_HEADER;

			// tinfl_decompress_mem_to_heap allocates memory for the decompressed data.
			// This is memory efficient as it only allocates what's needed, and handles
			// potential growth if the decompressed size is much larger than compressed.
			//void *decompressed_data = NULL;
			 size_t decompressed_data;
#if 0
			decompressed_data = tinfl_decompress_mem_to_heap(
					(void *)(&reassembly_buff[rx_msg][0]), // Input buffer (from pbuf)
					MAX_MSG_SIZE/*134*/,     // Input buffer length
					&decompressed_len, // Output: actual decompressed length
					inflate_flags      // Flags (e.g., Zlib header parsing)
					);
#endif
#if 1
				void *pSrc_buf = (void *)(&reassembly_buff[rx_msg][0]); // Input buffer (from pbuf)
				printf("size of disp buff is %d\n",sizeof(disp_buf));
//				decompressed_len = tinfl_decompress_mem_to_mem((void *)(&disp_buf[0]), sizeof(disp_buf), pSrc_buf, MAX_MSG_SIZE, inflate_flags);
				//decompressed_len = tinfl_decompress_mem_to_mem((void *)(&disp_buf[0]), sizeof(disp_buf), pSrc_buf, 836, inflate_flags);
				deinflate_payload(rx_msg);
#if 0
			if (decompressed_len > 0) {

				printf("INFO: Successfully decompressed  to %d bytes.\n",
						 (int)decompressed_len);

				// --- Scaffolding: Process Decompressed Data ---
				// Ensure the decompressed data is null-terminated if you intend to print it as a string
				// or use string functions. Add a null terminator if space allows.
				// Note: If decompressed_len is exactly the buffer size, adding null might overflow.
				// For safety, allocate 1 extra byte for null terminator if needed.
				// For printing, we can use '%.*s' which handles non-null-terminated strings.
				printf("DECOMPRESSED DATA: '%d'\n", (int)decompressed_len);

				// Add your specific data processing logic here using 'decompressed_data'
				// and 'decompressed_len'.
				// Free the dynamically allocated decompressed data.
				//MZ_FREE(decompressed_data); // Uses 'free()' internally
			} else {
				printf("ERROR: Decompression failed for packet \n");
				// You might want to log the specific tinfl_status if you use the
				// tinfl_decompress function directly for more detailed error codes.
			}
#endif

#endif




		//	vTaskDelay(pdMS_TO_TICKS(1000)); // Nothing to do, LWIP runs in background
		}
	}
    }
}


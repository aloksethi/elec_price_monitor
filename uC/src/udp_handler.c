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
#include "hardware/adc.h"
#include "pico/cyw43_arch.h"
#include "config.h"
#include "miniz.h"
#include "globals.h"

#define UDP_DATA_RECEIVED_BIT (1UL << 0UL) // Bit 0: Set when UDP data arrives
#define UDP_TIMER_FIRED_BIT   (1UL << 1UL) // Bit 1: Set when the periodic timer fires



static uint8_t g_empty_idx = 0;
static struct udp_pcb *g_pcb;

static QueueHandle_t g_udp_rx_queue;
//static EventGroupHandle_t g_udp_evnt_grp;
static tinfl_decompressor decomp; //allocate globally, needs a lot of memeory on stack otherwise

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

		// We check if we have received all the data for the full message.
		if (reassembly_len >= expected_msg_len)// - offsetof(msg_t, data))) 
		{
            udp_qmsg_t qmsg;
			BaseType_t xHigherPriorityTaskWoken;
			printf("Full message reassembled. Total payload length: %d\n", reassembly_len);
            qmsg.idx = g_empty_idx;
            qmsg.msg_type = msg_p->msg_type;
            qmsg.msg_len = reassembly_len;
			// Reset for the next message
			reassembly_len = 0;
			expected_seq_num = 0;
			if (xQueueSendFromISR(g_udp_rx_queue, &qmsg, &xHigherPriorityTaskWoken) == pdPASS) 
			{
				// If successfully sent to queue, signal the udp_task that data is available.
				g_empty_idx = (g_empty_idx + 1)%MAX_DATA_BUFS;
				//xEventGroupSetBitsFromISR(g_udp_evnt_grp, UDP_DATA_RECEIVED_BIT, &xHigherPriorityTaskWoken);
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

 
  
//#define MAX_DECOMPRESSED_PAYLOAD_SIZE 4096
//static uint8_t decompressed_output_buffer[MAX_DECOMPRESSED_PAYLOAD_SIZE];
static int8_t deinflate_payload(uint8_t rx_msg_idx, uint8_t * p_dst)
{
	size_t in_buf_size = MAX_MSG_SIZE;//rx_msg.len;
	size_t out_buf_size = DISP_BUFF_SIZE; 
	void *p_src_buf;
	int inflate_flags;
	int8_t ret_val;
	// Initialize the decompressor for each new decompression operation.
	tinfl_init(&decomp);

	// TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF is important as our output buffer is fixed.
	inflate_flags = TINFL_FLAG_PARSE_ZLIB_HEADER | TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF;

	p_src_buf = (void *)(&reassembly_buff[rx_msg_idx][0]); // Input buffer (from pbuf)
	tinfl_status status = tinfl_decompress(
			&decomp,                   // Static decompressor state
			(const mz_uint8*)p_src_buf, // Input buffer (contiguous)
			&in_buf_size,              // Input size (will be updated by tinfl)
			p_dst, // Static output buffer
			p_dst, // Static output buffer
			&out_buf_size,             // Output buffer capacity (will be updated by tinfl)
			inflate_flags
			);

	if (status == TINFL_STATUS_DONE) {
		ret_val = 0;
		printf("INFO: Successfully decompressed to %d bytes.\n",
				(int)out_buf_size); // out_buf_size now holds actual decompressed length

	} else if (status == TINFL_STATUS_HAS_MORE_OUTPUT) {
		printf("ERROR: Decompression failed: Output buffer too small \n");
		ret_val = -1;
		// This indicates MAX_DECOMPRESSED_PAYLOAD_SIZE needs to be increased.
	} else {
		printf("ERROR: Decompression failed with status %d \n",
				status);
		ret_val = -2;
	}
	return ret_val;
}

//#define PICO_VSYS_PIN 29


void read_batt_charge(uint8_t *batt_level) 
{
    int ignore_count = PICO_POWER_SAMPLE_COUNT;
    float meas_v;
    uint32_t vsys = 0;
    const float conversion_factor = 3.3f / (1 << 12);

    adc_init();
    cyw43_thread_enter();
    // Make sure cyw43 is awake
    cyw43_arch_gpio_get(CYW43_WL_GPIO_VBUS_PIN);

    // setup adc
    adc_gpio_init(PICO_VSYS_PIN);
    adc_select_input(PICO_VSYS_PIN - PICO_FIRST_ADC_PIN);

    adc_fifo_setup(true, false, 0, false, false);
    adc_run(true);
    //printf("vsys_pin:%d, gpio_vbus_pin: %d\n", PICO_VSYS_PIN, CYW43_WL_GPIO_VBUS_PIN);
    // We seem to read low values initially - this seems to fix it
    while (!adc_fifo_is_empty() || ignore_count-- > 0) 
    {
        (void)adc_fifo_get_blocking();
    }
    // read vsys
    for(int i = 0; i < PICO_POWER_SAMPLE_COUNT; i++) {
        uint16_t val = adc_fifo_get_blocking();
        vsys += val;
    }
    adc_run(false);
    adc_fifo_drain();

    vsys /= PICO_POWER_SAMPLE_COUNT;

    cyw43_thread_exit();
    // Generate voltage
    meas_v = vsys * 3 * conversion_factor;
    //	printf("voltage: %f \n", meas_v);
    //	rough levels for a li-ion cell
    if (meas_v > 4.0) *batt_level = 100;
    else if (meas_v > 3.7) *batt_level = 75;
    else if (meas_v > 3.5) *batt_level = 50;
    else if (meas_v > 3.3) *batt_level = 25;
    else *batt_level = 5;

    return ;
}
void send_udp_packet(uint8_t * payload, uint8_t payload_len)
{
	ip_addr_t dest_ip;
	int32_t err;
    struct pbuf *p = pbuf_alloc(PBUF_TRANSPORT, payload_len, PBUF_RAM);
    if (p) 
	{
        memcpy(p->payload, payload, payload_len);
        ipaddr_aton(PYTHON_IP_ADD, &dest_ip);

        err = udp_sendto(g_pcb, p, &dest_ip, PY_PORT);
        pbuf_free(p);
		if (err)
		{
			printf("udp_sendto failed: %d\n", err);
		}
    }
	else
	{
		printf("Error:failed to allocate udp_send data\n");
	}

    return;
}

void send_battery_level()
{
        uint8_t batt_level;

        read_batt_charge(&batt_level);

	udp_msg_t *p_data;
	uint16_t payload_len = sizeof(udp_msg_t) + 1;
	p_data = (udp_msg_t *)malloc(payload_len);

	if(p_data)
	{
		p_data->msg_type = MSG_TYPE_BATT_STATUS;
		p_data->msg_len = htons(payload_len);
		p_data->seq_num = 0;
		p_data->data[0] = batt_level;

		send_udp_packet((uint8_t *)p_data, payload_len);
	}
	else
	{
		printf("Error:failed to allocate data for sending battery level\n");
	}
	free(p_data);

    return;
}
void req_img_data(uint32_t type)
{
	udp_msg_t *p_data;
	uint16_t payload_len = sizeof(udp_msg_t);
	p_data = (udp_msg_t *)malloc(payload_len);

	if(p_data)
	{
		p_data->msg_type = type;
		p_data->msg_len = htons(payload_len);
		p_data->seq_num = 0;

		send_udp_packet((uint8_t *)p_data, payload_len);
	}
	else
	{
		printf("Error:failed to allocate data for sending image data\n");
	}
	free(p_data);
    return;
}
void req_rimg_data()
{
	req_img_data(MSG_TYPE_REQ_RIMG_DATA);
}
void req_bimg_data()
{
	req_img_data(MSG_TYPE_REQ_BIMG_DATA);
}


extern volatile uint8_t g_do_not_sleep;
void udp_task(void *params) 
{
    uint8_t tmp=0;
    g_pcb = udp_new();
    if (!g_pcb) {
        printf("Failed to create UDP PCB\n");
        vTaskDelete(NULL);
    }

    g_udp_rx_queue = xQueueCreate(MAX_DATA_BUFS, sizeof(udp_msg_t));
    if (g_udp_rx_queue == NULL)
    {
        printf("failed to create udp rx queue\n");
        return;
    }
    udp_bind(g_pcb, IP_ADDR_ANY, UC_PORT);
    udp_recv(g_pcb, udp_rx_callback, NULL); // creat the queue before regitering the callbacak
#if 0
    g_udp_evnt_grp = xEventGroupCreate();
    if (g_udp_evnt_grp == NULL) {
        printf("FATAL: Failed to create UDP Event Group. Cannot start task.\n");
        return;
    }
#endif		

    while (1) {
        EventBits_t uxBits;
        udp_qmsg_t qmsg;

			printf("waiting the semaphre\n");

        if (xSemaphoreTake(g_wifi_ready_sem, portMAX_DELAY) == pdTRUE)
        {
			printf("got the semaphre\n");
            // 1) Send battery level
            send_battery_level();

            while (1)
            {
                // 2) Request RED image
                req_rimg_data();

                if (xQueueReceive(g_udp_rx_queue, &qmsg, pdMS_TO_TICKS(UDP_CHUNK_TIMEOUT_MS)) == pdPASS)
                {
                    printf("INFO: Received, queue index:%d, msg_type:%d\n", qmsg.idx, qmsg.msg_type);
                    if (qmsg.msg_type != MSG_TYPE_RIMG_DATA)
                    {
                        printf("wrong message type received?expecteing red data\n");
                        continue;
                    }
                    int8_t ret_val;
                    ret_val = deinflate_payload(qmsg.idx, rimg_buf);
                    if (ret_val == 0)
                        break;
                }
                else
                    continue;
            }
            // tell epaer to display red data xQueueSend(epaper_queue, &display_cmd, portMAX_DELAY);
            while (1)
            {
                // 4) Request BLACK image
                req_bimg_data();
                if (xQueueReceive(g_udp_rx_queue, &qmsg, pdMS_TO_TICKS(UDP_CHUNK_TIMEOUT_MS)) == pdPASS)
                {
                    printf("INFO: Received, queue index:%d, msg_type:%d\n", qmsg.idx, qmsg.msg_type);
                    if (qmsg.msg_type != MSG_TYPE_BIMG_DATA)
                    {
                        printf("wrong message type received?expecteing black data\n");
                        continue;
                    }
                    int8_t ret_val;
                    ret_val = deinflate_payload(qmsg.idx, bimg_buf);
                    if (ret_val == 0)
                        break;
                }
                else
                    continue;
            }
            // tell epaer to display data 
            xTaskNotifyGive( g_th_epaper );  

            // have to sleep now, will send a message
            send_battery_level();
            xEventGroupSync( g_sleep_eg, SLEEP_EG_UDP_DONE_BIT, ALL_SYNC_BITS, portMAX_DELAY );
            //g_do_not_sleep = 0;
#if 0
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
                while (xQueueReceive(g_udp_rx_queue, &qmsg, 0) == pdPASS) 
                { 
                    printf("INFO: Received, queue index:%d, msg_type:%d\n", qmsg.idx, qmsg.msg_type);

                    switch (qmsg.msg_type)
                    {
                        case MSG_TYPE_RIMG_DATA:
                            {
                                int8_t ret_val;
                                float v;
                                ret_val = deinflate_payload(qmsg.idx);


                                g_do_not_sleep = 0;
                                break;
                            }
                        case MSG_TYPE_BIMG_DATA:
                            {
                                deinflate_payload(qmsg.idx);
                                g_do_not_sleep = 0;

                                break;
                            }
                        case MSG_TYPE_TIME_SYNC:
                            {

                            }
                        default:
                            printf("unhandled message type received:%d\n", qmsg.msg_type);
                    }


                    //	vTaskDelay(pdMS_TO_TICKS(1000)); // Nothing to do, LWIP runs in background
                }
            }
#endif
        }
    }
}


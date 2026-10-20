/* 
 * This file is part of the GDoor distribution (https://github.com/gdoor-org).
 * Copyright (c) 2024 GDoor authors.
 * 
 * This program is free software: you can redistribute it and/or modify  
 * it under the terms of the GNU General Public License as published by  
 * the Free Software Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but 
 * WITHOUT ANY WARRANTY; without even the implied warranty of 
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License 
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
#include "driver/gpio.h"
#include "driver/gptimer.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "defines.h"
#include "gdoor_rx.h"
#include "gdoor_data.h"
#include "gdoor_utils.h"
#include "printer_helper.h"

namespace GDOOR_RX {

    static const char *TAG = "gdoor_rx";

    uint16_t counts[MAX_WORDLEN*9]; // Received counter values of bitstream, buffer
    volatile uint16_t isr_cnt = 0; // Interrupt Counter (Counting RX edges)

    uint8_t words[MAX_WORDLEN]; //Received words buffer
    uint16_t raw[MAX_WORDLEN*9]; // Received raw counter values of bitstream

    volatile uint16_t rx_state = 0; // State Machine

    volatile uint8_t bitcounter = 0; //Current bit index, in currently active bitstream

    volatile bool enabled = false; // RX is switched off while we send, so we do not receive our own message
    volatile bool bit_pending = false; // Edges were counted since the last bit end
    volatile uint64_t last_edge = 0; // Timer count at the last RX edge

    GDOOR_DATA retval;

    // One free-running timer: the edge ISR moves its alarm to "bit is over",
    // the alarm then moves itself on to "bitstream is over".
    // So no timer is stopped or restarted from an ISR.
    gptimer_handle_t timer = NULL;

    gpio_num_t pin_rx = GPIO_NUM_NC;

    static inline void IRAM_ATTR set_alarm(uint64_t count) {
        gptimer_alarm_config_t alarm = {};
        alarm.alarm_count = count;
        gptimer_set_alarm_action(timer, &alarm);
    }

    /*
    * We received a 60kHz pulse, so (re)arm the timeout for this bit and increment bit pulse count,
    * so that logic knows how much pulses were in this bit pulse-train.
    */
    void IRAM_ATTR isr_extint_rx(void *arg) {
        if (!enabled) {
            return;
        }
        uint64_t now = 0;
        gptimer_get_raw_count(timer, &now);
        rx_state |= (uint16_t)FLAG_RX_ACTIVE;
        isr_cnt = isr_cnt + 1;
        last_edge = now;
        bit_pending = true;
        set_alarm(now + RX_BIT_END_TICKS); //Detect bit is over
    }

    /*
    * The alarm fires either after a bit or after the whole bitstream.
    * Bit: the rx 60kHz pulse-train stopped, so we read out how many pulses
    * we got for this bit (to decide 1 or 0) and wait for the bitstream end.
    * Bitstream: no further bit followed, rx bit stream is over.
    */
    bool IRAM_ATTR isr_timer_alarm(gptimer_handle_t t, const gptimer_alarm_event_data_t *edata, void *arg) {
        if (bit_pending) {
            if (bitcounter >= MAX_WORDLEN*9) {
                bitcounter = 0;
            }
            counts[bitcounter] = isr_cnt;

            isr_cnt = 0;
            bitcounter = bitcounter + 1;
            bit_pending = false;
            set_alarm(last_edge + RX_BITSTREAM_END_TICKS); //Detect bitstream is over
        } else {
            rx_state &= (uint16_t)~FLAG_RX_ACTIVE;
            rx_state |= (uint16_t)FLAG_BITSTREAM_RECEIVED;
            gptimer_set_alarm_action(t, NULL);
        }
        return false;
    }

    /*
    * Internal function set reset all internal values.
    */
    static void IRAM_ATTR reset() {
        bitcounter = 0;
        isr_cnt = 0;
        bit_pending = false;
    }

    /*
    * Function to enable/disable RX, so that during TX we can disable RX to not get our own message.
    * Called from the TX timer ISR when sending is done.
    */
    void IRAM_ATTR enable() {
        reset();
        enabled = true;
    }

     /*
    * Function to enable/disable RX, so that during TX we can disable RX to not get our own message
    */
    void IRAM_ATTR disable() {
        enabled = false;
        reset();
    }


    /*
    * Function called by user to setup everything needed for GDoor.
    * @param int rxpin Pin number where pulses from bus are received
    */
    void setup(uint8_t rxpin) {
        reset();
        pin_rx = (gpio_num_t) rxpin;

        retval.len = 0;
        retval.valid = 0;

        // Timer counting at 120kHz, its alarm detects bit and bitstream end
        gptimer_config_t timer_config = {};
        timer_config.clk_src = GPTIMER_CLK_SRC_DEFAULT;
        timer_config.direction = GPTIMER_COUNT_UP;
        timer_config.resolution_hz = RX_TIMER_HZ;
        esp_err_t err = gptimer_new_timer(&timer_config, &timer);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "No free timer for RX (%s)", esp_err_to_name(err));
            return;
        }
        gptimer_event_callbacks_t callbacks = {};
        callbacks.on_alarm = isr_timer_alarm;
        gptimer_register_event_callbacks(timer, &callbacks, NULL);
        gptimer_enable(timer);
        gptimer_start(timer);

        // External RX interrupt on the falling edge of every pulse
        gpio_config_t io_config = {};
        io_config.pin_bit_mask = 1ULL << pin_rx;
        io_config.mode = GPIO_MODE_INPUT;
        io_config.pull_up_en = GPIO_PULLUP_DISABLE;
        io_config.pull_down_en = GPIO_PULLDOWN_DISABLE;
        io_config.intr_type = GPIO_INTR_NEGEDGE;
        gpio_config(&io_config);

        // Arduino or another component may have installed the ISR service already
        err = gpio_install_isr_service(GDOOR_ISR_IRAM_SAFE ? ESP_INTR_FLAG_IRAM : 0);
        if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
            ESP_LOGE(TAG, "GPIO ISR service failed (%s)", esp_err_to_name(err));
            return;
        }
        gpio_isr_handler_add(pin_rx, isr_extint_rx, NULL);

        // Enable External RX Interrupt
        enable();
    }

    /*
    * Function called by user, in main loop.
    * Needed for the decoding logic.
    */
    void loop() {
        if (rx_state & FLAG_BITSTREAM_RECEIVED) {
            rx_state &= (uint16_t)~FLAG_BITSTREAM_RECEIVED;
            JSONDEBUG("Gira RX done");
            if (retval.parse(counts, bitcounter)) {
                JSONDEBUG("Gira RX was successfully parsed");
                rx_state |= FLAG_DATA_READY;
            }
            reset();
        }
    }

    /**
    * User function, called to see if new data is available.
    * @return Data pointer as GDOOR_RX_DATA class or NULL if no data is available
    */
    GDOOR_DATA* read() {
        if(rx_state & FLAG_DATA_READY) {
            rx_state &= (uint16_t)~FLAG_DATA_READY;
            return &retval;
        }
        return NULL;
    }
}

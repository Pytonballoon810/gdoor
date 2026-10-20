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
#include <string.h>
#include "driver/gpio.h"
#include "driver/gptimer.h"
#include "driver/ledc.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "defines.h"
#include "gdoor_tx.h"
#include "gdoor_rx.h"
#include "gdoor_utils.h"

namespace GDOOR_TX {
    static const char *TAG = "gdoor_tx";

    volatile uint16_t tx_state = 0;
    uint16_t tx_words[MAX_WORDLEN];
    uint8_t tx_strbuffer[MAX_WORDLEN*2];
    uint8_t last_data[MAX_WORDLEN]; // Last accepted message incl. CRC, so it can be reported back to the user
    uint16_t last_len = 0;
    volatile uint16_t bits_len = 0;
    volatile uint16_t bits_ptr = 0;
    volatile uint16_t pulse_cnt = 0;
    volatile uint8_t startbit_send = 0;

    volatile uint8_t timer_oc_state = 0;

    gpio_num_t pin_tx = GPIO_NUM_NC;
    gpio_num_t pin_tx_en = GPIO_NUM_NC;

    gptimer_handle_t timer_60khz = NULL;

    static inline uint16_t IRAM_ATTR bit2pulselen(uint16_t bit) {
        if (bit) {
            return ONE_PULSENUM;
        } else {
            return ZERO_PULSENUM;
        }
    }

    static inline uint16_t IRAM_ATTR extractBitLen(uint16_t word, uint8_t bitindex) {
        return bit2pulselen((uint16_t) (word & (uint16_t)(0x01<<bitindex))); //LSB first
    }

    static inline uint16_t byte2word(uint8_t byte) {
        uint16_t value = byte & 0x00FF;
        if(GDOOR_UTILS::parity_odd(byte)) { //If parity, set MSB
            value |= 0x100;
        }
        return value;
    }

    /*
    * Carrier on/off. The LEDC duty is set once in setup(),
    * gating only enables and disables the channel output (both are ISR safe).
    */
    static inline void IRAM_ATTR pwm_on() {
        ledc_update_duty(LEDC_LOW_SPEED_MODE, TX_LEDC_CHANNEL);
    }

    static inline void IRAM_ATTR pwm_off() {
        ledc_stop(LEDC_LOW_SPEED_MODE, TX_LEDC_CHANNEL, 0);
    }

    static inline void start_timer() {
        tx_state |= STATE_SENDING;
        bits_ptr = 0;
        pulse_cnt = 0;
        timer_oc_state = 0;
        startbit_send = 0;

        //Workaround: Disable comparator to not be disturbed by receive.
        //Better sending scheme is needed
        GDOOR_RX::disable();

        //TX Enable Pin high
        gpio_set_level(pin_tx_en, 1);

        gptimer_set_raw_count(timer_60khz, 0);
        gptimer_start(timer_60khz); //Start timer to send out bitstream
    }

    static inline void IRAM_ATTR stop_timer() {
        bits_ptr = 0;
        pulse_cnt = 0;
        startbit_send = 0;

        // PWM off
        pwm_off();

        //TX Enable Pin Low
        gpio_set_level(pin_tx_en, 0);
        gptimer_stop(timer_60khz); // Fails harmlessly if the timer is not running
        tx_state &= (uint16_t)~STATE_SENDING;
        //Workaround: Enable comparator after sending
        //Better sending scheme is needed
        GDOOR_RX::enable();
    }


    /*
    * This is the sending timer interrupt
    */
    bool IRAM_ATTR isr_timer_60khz(gptimer_handle_t timer, const gptimer_alarm_event_data_t *edata, void *arg) {
        if(pulse_cnt == 0) { // Update timer, we send out (or waited) enough timer ticks to go to next bit
            if (bits_ptr >= bits_len || bits_ptr >= MAX_WORDLEN*9) {//We send everything
                stop_timer();
                return false;
            }

            if(timer_oc_state == 1) {
                // Do not send next 60khz pulses, but send pause (nothing)
                timer_oc_state = 0;
                pulse_cnt = PAUSE_PULSENUM;
                pwm_off(); //disable timer pulse output to send pause
            } else {
                // Load new tick values
                if (!startbit_send) { //First bit, is start bit with fixed value
                    pulse_cnt = STARTBIT_PULSENUM;
                    startbit_send = 1;
                } else { //Startbit was send, so load bit values now
                    uint8_t wordindex = (uint8_t) (bits_ptr/9);
                    uint8_t bitindex = (uint8_t) (bits_ptr%9);
                    uint16_t word = tx_words[wordindex];

                    pulse_cnt = extractBitLen(word, bitindex);
                    bits_ptr = bits_ptr + 1;
                }

                timer_oc_state = 1; //Signal that we are sending, so next time a pause will happen
                pwm_on(); //Enable timer pulse output to send pulses forming the bit
            }
        } else { // Just update timer ticks, we are not finished yet
            pulse_cnt = pulse_cnt - 1;
        }
        return false;
    }

    /*
    * Function called by user to setup everything needed for GDoor.
    * @param int txpin Pin number where PWM is created when sending out data
    * @param int txenpin Pin number where output buffer is turned on/off
    */
    void setup(uint8_t txpin, uint8_t txenpin) {
        pin_tx = (gpio_num_t) txpin;
        pin_tx_en = (gpio_num_t) txenpin;

        gpio_config_t io_config = {};
        io_config.pin_bit_mask = (1ULL << pin_tx) | (1ULL << pin_tx_en);
        io_config.mode = GPIO_MODE_OUTPUT;
        gpio_config(&io_config);
        gpio_set_level(pin_tx_en, 0);
        gpio_set_level(pin_tx, 0);

        // Timer ticking at 60kHz, one alarm per bus pulse
        gptimer_config_t timer_config = {};
        timer_config.clk_src = GPTIMER_CLK_SRC_DEFAULT;
        timer_config.direction = GPTIMER_COUNT_UP;
        timer_config.resolution_hz = TX_TIMER_HZ;
        esp_err_t err = gptimer_new_timer(&timer_config, &timer_60khz);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "No free timer for TX (%s)", esp_err_to_name(err));
            return;
        }
        gptimer_event_callbacks_t callbacks = {};
        callbacks.on_alarm = isr_timer_60khz;
        gptimer_register_event_callbacks(timer_60khz, &callbacks, NULL);

        // Call isr_timer_60khz after every 60kHz cycle
        gptimer_alarm_config_t alarm = {};
        alarm.alarm_count = 1;
        alarm.reload_count = 0;
        alarm.flags.auto_reload_on_alarm = true;
        gptimer_set_alarm_action(timer_60khz, &alarm);
        gptimer_enable(timer_60khz);

        //Setup PWM subsystem (LEDC) on pin_tx
        // We only modulate with 52kHz, as the bandpass
        // manufacturing tolerances are a bit on the lower side.
        // Still works.
        ledc_timer_config_t pwm_timer = {};
        pwm_timer.speed_mode = LEDC_LOW_SPEED_MODE;
        pwm_timer.duty_resolution = TX_PWM_RESOLUTION;
        pwm_timer.timer_num = TX_LEDC_TIMER;
        pwm_timer.freq_hz = TX_PWM_HZ;
        pwm_timer.clk_cfg = LEDC_AUTO_CLK;
        err = ledc_timer_config(&pwm_timer);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "TX PWM timer failed (%s)", esp_err_to_name(err));
            return;
        }

        // Channel starts with duty 0; the real duty only becomes active with pwm_on()
        ledc_channel_config_t pwm_channel = {};
        pwm_channel.gpio_num = pin_tx;
        pwm_channel.speed_mode = LEDC_LOW_SPEED_MODE;
        pwm_channel.channel = TX_LEDC_CHANNEL;
        pwm_channel.intr_type = LEDC_INTR_DISABLE;
        pwm_channel.timer_sel = TX_LEDC_TIMER;
        pwm_channel.duty = 0;
        pwm_channel.hpoint = 0;
        ledc_channel_config(&pwm_channel);
        ledc_set_duty(LEDC_LOW_SPEED_MODE, TX_LEDC_CHANNEL, TX_PWM_DUTY);
        pwm_off();

        bits_ptr = 0;
        pulse_cnt = 0;
        startbit_send = 0;
        bits_len = 0;
        tx_state = 0;
    }

    /*
    * Function called by user to send out data.
    * @param data buffer with bus data
    * @param len length of buffer, can be max MAX_WORDLEN
    * @return true if the data was accepted and transmission started
    */
    bool send(uint8_t *data, uint16_t len) {
        if (timer_60khz != NULL && ! (tx_state & STATE_SENDING) && len > 0 && len < MAX_WORDLEN) {
            bits_ptr = 0;
            pulse_cnt = 0;
            bits_len = (uint16_t) (len*9 + 9); // Data bits + CRC (8bit CRC data + parity bit) (Startbit is added by timer int. routine)


            for (uint16_t i=0; i<len; i++) {
                uint8_t byte = data[i];
                tx_words[i] = byte2word(byte);
            }

            uint8_t crc = GDOOR_UTILS::crc(data, len);
            tx_words[len] = byte2word(crc);

            memcpy(last_data, data, len);
            last_data[len] = crc;
            last_len = len + 1;

            start_timer();
            return true;
        }
        return false;
    }

    /*
    * Value of one hex digit, upper or lower case.
    * @return 0..15, or -1 if c is no hex digit
    */
    static int hex_value(char c) {
        if (c >= '0' && c <= '9') {
            return c - '0';
        }
        if (c >= 'A' && c <= 'F') {
            return c - 'A' + 10;
        }
        if (c >= 'a' && c <= 'f') {
            return c - 'a' + 10;
        }
        return -1;
    }

    /*
    * Function called by user to send out data.
    * @param hex string data without 0x prefix
    * @return true if the string was valid hex data and transmission started
    */
    bool send(const char *str) {
        uint16_t index = 0;
        size_t len = (str == NULL) ? 0 : strlen(str);

        // Only if we have enough memory
        if(len > 0 && len < MAX_WORDLEN*2) {
            // Convert from hex string to raw buffer array
            for(size_t i=0; i+1<len; i+=2) { //i+1 must stay inside the string
                int high = hex_value(str[i]);
                int low = hex_value(str[i+1]);
                if (high >= 0 && low >= 0) { // Check if input can be decoded as 8 bit hex value
                    tx_strbuffer[index] = high << 4 | low;
                    index++;
                } else { // Abort on parse error
                    index = 0;
                    break;
                }
            }

            // If something was converted, transmit it
            if (index > 0) {
                return send(tx_strbuffer, index);
            }
        }
        return false;
    }
}

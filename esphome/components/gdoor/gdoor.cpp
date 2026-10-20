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
#include "soc/soc_caps.h"
#if SOC_DAC_SUPPORTED
#include "driver/dac_oneshot.h"
#include "soc/dac_channel.h"
#endif
#include "gdoor.h"

namespace GDOOR {
    /*
    * Setup everything needed for GDoor.
    * @param int txpin Pin number where PWM is created when sending out data
    * @param int txenpin Pin number where output buffer is turned on/off
    * @param int rxpin Pin number where pulses from bus are received
    */
    void setup(uint8_t txpin, uint8_t txenpin, uint8_t rxpin) {
        GDOOR_RX::setup(rxpin);
        GDOOR_TX::setup(txpin, txenpin);
    }

    /*
    * RX loop, needs to be called in main loop()
    * Needed for the decoding logic.
    */
    void loop() {
        GDOOR_RX::loop();
    }

    /**
    * User function, called to see if new data is available.
    * @return Data pointer as GDOOR_RX_DATA class or NULL if no data is available
    */
    GDOOR_DATA* read() {
        return GDOOR_RX::read();
    }

    GDOOR_DATA sent_data; // Copy of the last transmitted message, handed out by sent()
    bool sent_pending = false; // A transmission was started and not yet reported via sent()

    /*
    * Send out data.
    * @param data buffer with bus data
    * @param len length of buffer, can be max MAX_WORDLEN
    * @return true if the data was accepted and transmission started
    */
    bool send(uint8_t *data, uint16_t len) {
        bool accepted = GDOOR_TX::send(data, len);
        sent_pending = sent_pending || accepted;
        return accepted;
    }

    /*
    * Send out data.
    * @param hex string data without 0x prefix
    * @return true if the string was valid hex data and transmission started
    */
    bool send(const char *str) {
        bool accepted = GDOOR_TX::send(str);
        sent_pending = sent_pending || accepted;
        return accepted;
    }

    /**
    * User function, called to see if a transmission finished since the last call.
    * Returns the message as it was put on the bus (including CRC),
    * so that it can be reported back, e.g. via MQTT.
    * @return Data pointer as GDOOR_DATA class or NULL if nothing was sent
    */
    GDOOR_DATA* sent() {
        if (!sent_pending || (GDOOR_TX::tx_state & STATE_SENDING)) {
            return NULL;
        }
        sent_pending = false;
        memcpy(sent_data.data, GDOOR_TX::last_data, GDOOR_TX::last_len);
        memset(sent_data.raw, 0, sizeof(sent_data.raw));
        sent_data.len = GDOOR_TX::last_len;
        sent_data.valid = 1;
        return &sent_data;
    }

    /*
    * GDOOR activity status
    * @return true: GDOOR RX or TX is active. False: no GDOOR activity.
    */
    bool active() {
        return (GDOOR_TX::tx_state != 0 || GDOOR_RX::rx_state != 0);
    }

    /** Set RX Threshold (Sensitivity) to a certain level,
     * only working for IO22 rx input on v3.1 hardware
     * @param pin DAC pin driving the comparator threshold (GPIO25 or GPIO26 on the ESP32)
     * @param sensitivity Threshold in volts
    */
   void setRxThreshold(uint8_t pin, float sensitivity) {
#if SOC_DAC_SUPPORTED
        static dac_oneshot_handle_t dac = NULL;
        static uint8_t dac_pin = 0;
        uint8_t value =  (uint8_t)((sensitivity/3.3)*255);

        if (dac != NULL && dac_pin != pin) {
            dac_oneshot_del_channel(dac);
            dac = NULL;
        }
        if (dac == NULL) {
            dac_oneshot_config_t config = {};
            if (pin == DAC_CHAN0_GPIO_NUM) {
                config.chan_id = DAC_CHAN_0;
            } else if (pin == DAC_CHAN1_GPIO_NUM) {
                config.chan_id = DAC_CHAN_1;
            } else {
                return; // No DAC on this pin
            }
            if (dac_oneshot_new_channel(&config, &dac) != ESP_OK) {
                dac = NULL;
                return;
            }
            dac_pin = pin;
        }
        dac_oneshot_output_voltage(dac, value);
#endif
        // Chips without DAC (e.g. ESP32-S3) have a fixed comparator threshold
   }
}
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
#include "gdoor_component.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <cctype>

// Bus core shared with the Arduino firmware (copied by tools/sync_esphome_core.py)
#include "gdoor.h"

// The core's debug macros print JSON to Serial when this is set, which would
// interleave with the ESPHome logger. ESPHome logs the messages itself instead.
bool debug = false;

namespace esphome::gdoor {

static const char *const TAG = "gdoor";

static std::string to_hex(const uint8_t *data, size_t len) {
  static const char *const digits = "0123456789ABCDEF";
  std::string out;
  out.reserve(len * 2);
  for (size_t i = 0; i < len; i++) {
    out.push_back(digits[data[i] >> 4]);
    out.push_back(digits[data[i] & 0x0F]);
  }
  return out;
}

static GDoorMessage decode(GDOOR_DATA *data) {
  GDOOR_DATA_PROTOCOL protocol(data);
  GDoorMessage message;
  message.action = protocol.action;
  message.type = protocol.type;
  message.source = to_hex(protocol.source, sizeof(protocol.source));
  message.destination = to_hex(protocol.destination, sizeof(protocol.destination));
  message.parameters = to_hex(protocol.parameters, sizeof(protocol.parameters));
  message.busdata = to_hex(data->data, data->len);
  message.valid = data->valid;
  return message;
}

static std::string normalize_hex(const std::string &hex) {
  std::string out;
  for (char c : hex) {
    if (std::isxdigit(static_cast<unsigned char>(c)))
      out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  }
  return out;
}

std::string GDoorMessage::to_json() const {
  // Same field names as the MQTT firmware, so existing automations can be reused
  return "{\"action\": \"" + this->action + "\", \"parameters\": \"" + this->parameters + "\", \"source\": \"" +
         this->source + "\", \"destination\": \"" + this->destination + "\", \"type\": \"" + this->type +
         "\", \"busdata\": \"" + this->busdata + "\"}";
}

bool GDoorFilter::matches(const GDoorMessage &message) const {
  if (!this->actions.empty() &&
      std::find(this->actions.begin(), this->actions.end(), message.action) == this->actions.end())
    return false;
  if (!this->parameters.empty() && this->parameters != message.parameters)
    return false;
  if (!this->source.empty() && this->source != message.source)
    return false;
  if (!this->destination.empty() && this->destination != message.destination)
    return false;
  if (!this->busdata.empty() && this->busdata != message.busdata)
    return false;
  return true;
}

void GDoorComponent::setup() {
  if (this->rx_threshold_pin_ >= 0)
    GDOOR::setRxThreshold(this->rx_threshold_pin_, this->rx_sensitivity_);
  GDOOR::setup(this->tx_pin_, this->tx_enable_pin_, this->rx_pin_);
  // Bus messages are decoded from timer/interrupt data in loop(); a slow loop
  // can lose a message when the next one arrives before the previous was read.
  this->high_freq_.start();
}

void GDoorComponent::dump_config() {
  ESP_LOGCONFIG(TAG,
                "GDoor bus adapter:\n"
                "  RX pin: GPIO%u\n"
                "  TX pin: GPIO%u\n"
                "  TX enable pin: GPIO%u",
                this->rx_pin_, this->tx_pin_, this->tx_enable_pin_);
  if (this->rx_threshold_pin_ >= 0) {
    ESP_LOGCONFIG(TAG, "  RX threshold pin: GPIO%d (%.2f V)", this->rx_threshold_pin_, this->rx_sensitivity_);
  }
}

void GDoorComponent::send(const std::string &busdata) {
  std::string hex = normalize_hex(busdata);
  if (hex.empty() || hex.size() % 2 != 0 || hex.size() >= MAX_WORDLEN * 2) {
    ESP_LOGW(TAG, "Not sending invalid bus data '%s' (needs an even number of hex digits, max %u bytes)",
             busdata.c_str(), MAX_WORDLEN - 1);
    return;
  }
  this->tx_queue_.push_back(hex);
}

void GDoorComponent::loop() {
  GDOOR::loop();

  GDOOR_DATA *rx_data = GDOOR::read();
  if (rx_data != nullptr) {
    GDoorMessage message = decode(rx_data);
    if (message.valid) {
      // Logged at INFO so the busdata of e.g. the door opener can be copied from the log ("learning mode")
      ESP_LOGI(TAG, "Received %s (type %s, source %s, parameters %s), busdata: %s", message.action.c_str(),
               message.type.c_str(), message.source.c_str(), message.parameters.c_str(), message.busdata.c_str());
      this->message_callback_.call(message);
    } else if (this->log_invalid_) {
      ESP_LOGD(TAG, "Received invalid message (parity/CRC error), busdata: %s", message.busdata.c_str());
    }
  }

  GDOOR_DATA *tx_data = GDOOR::sent();
  if (tx_data != nullptr) {
    GDoorMessage message = decode(tx_data);
    ESP_LOGI(TAG, "Sent %s, busdata: %s", message.action.c_str(), message.busdata.c_str());
    this->sent_callback_.call(message);
  }

  if (!this->tx_queue_.empty() && !GDOOR::active()) {
    std::string hex = this->tx_queue_.front();
    this->tx_queue_.pop_front();
    if (!GDOOR::send(hex.c_str())) {
      ESP_LOGW(TAG, "Bus did not accept '%s'", hex.c_str());
    }
  }
}

#ifdef USE_EVENT
void GDoorEvent::setup() {
  this->parent_->add_on_message_callback([this](const GDoorMessage &message) {
    if (this->filter_.matches(message))
      this->trigger(message.action);
  });
}

void GDoorEvent::dump_config() { LOG_EVENT("", "GDoor Event", this); }
#endif

#ifdef USE_BUTTON
void GDoorButton::press_action() { this->parent_->send(this->busdata_); }

void GDoorButton::dump_config() {
  LOG_BUTTON("", "GDoor Button", this);
  ESP_LOGCONFIG(TAG, "  Bus data: %s", this->busdata_.c_str());
}
#endif

#ifdef USE_TEXT_SENSOR
void GDoorTextSensor::setup() {
  this->parent_->add_on_message_callback([this](const GDoorMessage &message) {
    switch (this->type_) {
      case GDOOR_TEXT_BUSDATA:
        this->publish_state(message.busdata);
        break;
      case GDOOR_TEXT_JSON:
        this->publish_state(message.to_json());
        break;
      case GDOOR_TEXT_ACTION:
      default:
        this->publish_state(message.action);
        break;
    }
  });
}

void GDoorTextSensor::dump_config() { LOG_TEXT_SENSOR("", "GDoor Text Sensor", this); }
#endif

}  // namespace esphome::gdoor

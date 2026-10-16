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
#pragma once

#include <deque>
#include <string>
#include <vector>

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"

#ifdef USE_EVENT
#include "esphome/components/event/event.h"
#endif
#ifdef USE_BUTTON
#include "esphome/components/button/button.h"
#endif
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

namespace esphome::gdoor {

/// One decoded bus message, all binary fields as uppercase hex strings.
struct GDoorMessage {
  std::string action;       // e.g. "BUTTON_RING"
  std::string type;         // e.g. "OUTDOOR"
  std::string source;       // 3 bytes, e.g. "A286FD"
  std::string destination;  // 3 bytes
  std::string parameters;   // 2 bytes, e.g. "0360" (which button was pressed)
  std::string busdata;      // complete message incl. CRC, can be sent again with gdoor.send
  bool valid{false};        // parity and CRC were correct

  std::string to_json() const;
};

/// Optional filter on a message, empty fields match everything.
struct GDoorFilter {
  std::vector<std::string> actions;
  std::string parameters;
  std::string source;
  std::string destination;
  std::string busdata;

  bool matches(const GDoorMessage &message) const;
};

class GDoorComponent : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

  void set_rx_pin(uint8_t pin) { this->rx_pin_ = pin; }
  void set_tx_pin(uint8_t pin) { this->tx_pin_ = pin; }
  void set_tx_enable_pin(uint8_t pin) { this->tx_enable_pin_ = pin; }
  void set_rx_threshold_pin(uint8_t pin) { this->rx_threshold_pin_ = pin; }
  void set_rx_sensitivity(float volts) { this->rx_sensitivity_ = volts; }
  void set_log_invalid(bool log_invalid) { this->log_invalid_ = log_invalid; }

  /// Queue a hex string (e.g. "020031ECF3EB0060A103C27A3D") for sending; sent as soon as the bus is idle.
  void send(const std::string &busdata);

  template<typename F> void add_on_message_callback(F &&callback) {
    this->message_callback_.add(std::forward<F>(callback));
  }
  template<typename F> void add_on_sent_callback(F &&callback) {
    this->sent_callback_.add(std::forward<F>(callback));
  }

 protected:
  uint8_t rx_pin_{22};
  uint8_t tx_pin_{25};
  uint8_t tx_enable_pin_{27};
  int16_t rx_threshold_pin_{-1};
  float rx_sensitivity_{1.45f};
  bool log_invalid_{false};

  std::deque<std::string> tx_queue_;
  HighFrequencyLoopRequester high_freq_;

  CallbackManager<void(const GDoorMessage &)> message_callback_;
  CallbackManager<void(const GDoorMessage &)> sent_callback_;
};

#ifdef USE_EVENT
class GDoorEvent : public event::Event, public Component {
 public:
  void set_parent(GDoorComponent *parent) { this->parent_ = parent; }
  void add_filter_action(const std::string &action) { this->filter_.actions.push_back(action); }
  void set_filter_parameters(const std::string &value) { this->filter_.parameters = value; }
  void set_filter_source(const std::string &value) { this->filter_.source = value; }
  void set_filter_destination(const std::string &value) { this->filter_.destination = value; }
  void set_filter_busdata(const std::string &value) { this->filter_.busdata = value; }
  void setup() override;
  void dump_config() override;

 protected:
  GDoorComponent *parent_{nullptr};
  GDoorFilter filter_;
};
#endif

#ifdef USE_BUTTON
class GDoorButton : public button::Button, public Component {
 public:
  void set_parent(GDoorComponent *parent) { this->parent_ = parent; }
  void set_busdata(const std::string &busdata) { this->busdata_ = busdata; }
  void dump_config() override;

 protected:
  void press_action() override;

  GDoorComponent *parent_{nullptr};
  std::string busdata_;
};
#endif

#ifdef USE_TEXT_SENSOR
enum GDoorTextSensorType : uint8_t {
  GDOOR_TEXT_ACTION,
  GDOOR_TEXT_BUSDATA,
  GDOOR_TEXT_JSON,
};

class GDoorTextSensor : public text_sensor::TextSensor, public Component {
 public:
  void set_parent(GDoorComponent *parent) { this->parent_ = parent; }
  void set_type(GDoorTextSensorType type) { this->type_ = type; }
  void setup() override;
  void dump_config() override;

 protected:
  GDoorComponent *parent_{nullptr};
  GDoorTextSensorType type_{GDOOR_TEXT_ACTION};
};
#endif

template<typename... Ts> class GDoorSendAction : public Action<Ts...> {
 public:
  explicit GDoorSendAction(GDoorComponent *parent) : parent_(parent) {}
  TEMPLATABLE_VALUE(std::string, busdata)

  void play(const Ts &...x) override { this->parent_->send(this->busdata_.value(x...)); }

 protected:
  GDoorComponent *parent_;
};

}  // namespace esphome::gdoor

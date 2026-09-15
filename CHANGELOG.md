# Changelog

## 0.2.0

- adds a third setup choice for a local ESPHome Bluetooth gateway
- keeps the existing ESPHome RS485 connection and its writable controls
- keeps the experimental read-only Zonergy Cloud connection
- recognizes the tested BLE companion firmware and exposes only its Zonergy
  entities, excluding unrelated sensors hosted on the same ESP32

## 0.1.1

HACS publication candidate. Repository metadata and validation were completed
successfully; no functional changes were made to the inverter communication.

## 0.1.0

First public release, tested with a Zonergy Venus6000-S1 inverter connected to
an ESP8266 D1 Mini through an RS485 transceiver.

### Included

- UI configuration through Home Assistant
- direct local connection to the ESPHome native API
- automatic reconnection and push state updates
- numeric, text and binary sensors
- charging switches and numeric controls already defined in the companion YAML
- Italian and English setup translations
- sanitized companion ESPHome firmware without private Wi-Fi credentials

### Safety note

Switches and numeric controls write to real inverter registers. Verify model,
limits and operating conditions before changing them.

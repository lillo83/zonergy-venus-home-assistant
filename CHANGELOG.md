# Changelog

## 0.3.0-beta.1

Charging from the grid on demand through the ESP8266 RS485 gateway. Tested on
a Zonergy Venus6000-S1; the BLE firmware and the cloud connection are
unchanged.

- adds a `select` platform to the integration, used by the new
  `Modalità Inverter` entity (Autoconsumo / TOU)
- companion ESP8266 firmware:
  - adds `Carica Batteria da Rete` with `Durata Carica da Rete`: it writes a
    charge window from the current time for the chosen duration, switches the
    inverter to TOU and returns it to self-consumption when the time is up,
    when switched off, or after a restart of the ESP8266
  - adds `Immetti FV in Rete`: between 06:00 and 22:00 it switches to TOU
    with the time slots moved to the night, so during the day the battery
    neither charges nor discharges and the PV surplus goes to the grid; it
    returns to self-consumption at the end of the duration or at 22:00
    (requires `Eccesso produzione FV = Connessione alla rete` in the app)
  - adds `Modalità Inverter` (register 2300: 0 = Autoconsumo, 1 = TOU),
    captured from the frames sent by the original Wi-Fi dongle
  - reads the two charge and discharge periods (registers 2728-2743, stored
    as ASCII digits) and shows them as `HH:MM`
  - adds `Esito Scrittura Fasce`, which reports whether each period was
    actually written
  - confirms that register 2957 (`Potenza Carica Forzata`) is the charging
    power set in the Zonergy app
  - makes the write-only controls (2955, 2956, 2957, 2962) template entities
    that remember the last value sent; the inverter rejects reads of these
    registers, which previously produced an error every polling cycle
  - turns `Forza Carica Batteria` off after a configurable maximum time or
    when Home Assistant disconnects
  - fixes the sign of `Potenza Prelievo Rete` and `Potenza Immissione Rete`
    (register 2403 is negative while importing), and therefore the daily
    imported and exported energy computed from them
- adds `zonergy-venus-esp8266-controlli.yaml`, a controls-only variant for
  installations that already read the inverter with the ESP32 Bluetooth
  firmware

Known limitation: on the tested inverter, the ESP8266 writes period 1 but the
write of period 2 (2736-2743) is not applied. `Carica Batteria da Rete` works
as long as period 2 in the Zonergy app does not overlap the requested charge
window (for example charge 00:00-06:00, discharge 22:00-23:59).

## 0.2.0

First stable release of the 0.2 series. It contains everything published in
the 0.2.0 betas; inverter communication is unchanged from 0.2.0-beta.17.

- adds a third setup choice for a local ESPHome Bluetooth gateway
- adds a self-healing watchdog to the companion BLE firmware: after 90 seconds
  without inverter packets it rebuilds the BLE connection, then restarts the
  ESP32 only if data does not resume
- adds maximum SOC, minimum SOC and their difference to the BLE firmware, next
  to the existing mean SOC entity (requires flashing the updated ESP32
  firmware; updating through HACS alone does not update the ESP32)
- allows changing the address and credentials of a configured ESPHome gateway
  from the integration options
- keeps the existing ESPHome RS485 connection and its writable controls
- keeps the experimental read-only Zonergy Cloud connection
- recognizes the tested BLE companion firmware and exposes only its Zonergy
  entities, excluding unrelated sensors hosted on the same ESP32
- no longer reports a fixed, outdated version number to the ESPHome gateway

## 0.2.0-beta.17 — 2026-10-01

- extends the BLE read at register 3004 from three to five words
- preserves the existing battery state-of-charge entity as mean SOC (3006)
- adds maximum SOC (3007), minimum SOC (3008) and their difference
- reports the new values as unknown for short replies or invalid SOC ranges
- documents the ESP32 firmware update required to obtain these measurements;
  updating the integration through HACS alone does not update the ESP32

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

# Zonergy Venus for Home Assistant

Custom integration for **Zonergy Venus hybrid inverters**. It supports a local
ESP8266/ESPHome RS485 gateway, a local ESP32 Bluetooth gateway for the original
Zonergy Wi-Fi dongle, or the same cloud service used by the official app.

> [!IMPORTANT]
> Version 0.2.0 adds an experimental, read-only Zonergy Cloud connection. The
> existing ESPHome mode is unchanged. Its switches and number controls write
> real values to the inverter, so use them only if their meaning and limits
> match your inverter model.

## How it works

Choose one connection during setup:

| Connection | Update method | Controls | Internet required |
|---|---|---|---|
| ESPHome RS485 | Local push, usually the fastest | Yes | No |
| ESPHome Bluetooth | Local push, live values about every 5 seconds | No, read-only | No |
| Zonergy Cloud (experimental) | Live read-only registers every 60 seconds, with dashboard fallback | No, read-only | Yes |

ESPHome reads the inverter over Modbus RTU. The integration opens one persistent
connection to the ESPHome native API (port `6053`) and receives state updates in
push mode. Bluetooth mode uses an ESP32 near the original Wi-Fi dongle and reads
its BLE register service locally; the dongle remains connected to Zonergy Cloud.
Cloud mode logs in with the same account as the Zonergy app, discovers
the associated inverter and reads its dashboards without requiring the dongle's
local IP address. It requests the inverter's read-only registers through the
official dongle cloud bridge once per minute and falls back to dashboard data if
the live request is unavailable.

Supported entities:

- PV, grid, load and battery measurements
- daily, monthly, yearly and cumulative energy values
- inverter and battery status
- ESP8266/RS485 online status
- grid/PV charging source and forced-charge switches
- forced-charge power and grid-charge limit controls

## Requirements

- Home Assistant with HACS installed
- Zonergy Venus compatible inverter
- for local mode: ESP8266 D1 Mini, TTL/RS485 transceiver and the companion
  ESPHome firmware in
  [`esphome/zonergy-venus-esp8266.yaml`](esphome/zonergy-venus-esp8266.yaml)
- for Bluetooth mode: ESP32 with Bluetooth support, placed within radio range
  of the original Zonergy Wi-Fi dongle, and the companion firmware in
  [`esphome/zonergy-venus-esp32-ble.yaml`](esphome/zonergy-venus-esp32-ble.yaml)
- for cloud mode: the original dongle online and a working Zonergy app account

The integration also accepts the original tested firmware as long as it exposes
the expected entities. The firmware included here is based on that working
configuration, with Wi-Fi credentials removed.

## Install for testing through HACS

1. In HACS open **Integrations**.
2. Open the menu in the upper-right corner and choose **Custom repositories**.
3. Add this URL:

   `https://github.com/lillo83/zonergy-venus-home-assistant`

4. Select category **Integration** and press **Add**.
5. Search for **Zonergy Venus**, open it and press **Download**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration**.
8. Search for **Zonergy Venus** and choose **ESPHome RS485 gateway**,
   **ESPHome Bluetooth gateway (original Wi-Fi dongle)**, or
   **Zonergy Cloud (experimental, original Wi-Fi dongle)**.

For ESPHome, use port `6053`. With the original firmware, leave both the
encryption key and legacy password empty. If API encryption is enabled in
ESPHome, enter the same key in the setup form.

Bluetooth mode is read-only and requires the companion ESP32 firmware. Copy
[`esphome/secrets.yaml.example`](esphome/secrets.yaml.example) to
`secrets.yaml`, then configure the Wi-Fi credentials, dongle Bluetooth address
and local PIN. Never publish a completed personal YAML containing those values.
The firmware updates live measurements every 5 seconds and the larger energy
counters about once per minute.

For cloud mode, enter the same account and password used in the Zonergy app.
Credentials remain in the Home Assistant configuration and are sent only to the
Zonergy service. Do not post them in issues or logs. Cloud availability and
refresh speed depend on the vendor service.

## ESPHome firmware

Copy the example firmware and create a `secrets.yaml` from
[`esphome/secrets.yaml.example`](esphome/secrets.yaml.example). The tested
wiring is:

| D1 Mini | Function | RS485 module |
|---|---|---|
| GPIO5 / D1 | UART TX | DI |
| GPIO2 / D4 | UART RX | RO |
| GPIO4 / D2 | Direction | DE + RE |

UART settings are `115200`, 8 data bits, no parity and 1 stop bit. Modbus slave
address is `1`.

## Writable registers

| Entity | Register | Range / values |
|---|---:|---|
| Charging source: Grid + PV | 2955 | `0` Grid + PV, `1` PV only |
| Force battery charging | 2956 | `1` enabled, `0` disabled |
| Forced charging power | 2957 | 100–5000 W, step 100 W |
| Grid charging limit | 2962 | 0–5000 W, step 100 W |

## Duplicate entities

If the standard ESPHome integration already manages this node, Home Assistant
may show two sets of inverter entities. During testing, keep only the set you
intend to use enabled.

## Troubleshooting

- Confirm that Home Assistant can reach the ESP8266 on TCP port `6053`.
- Assign the ESP8266 a DHCP reservation so its address does not change.
- For cloud mode, first confirm that the inverter is online and updating in the
  official Zonergy app. The dongle does not need to expose a web page locally.
- If setup reports an invalid gateway, flash the companion YAML or verify that
  `Potenza Totale PV`, `Potenza Carico` and `SOC Medio Batteria` are present.
- Open a GitHub issue and include the Home Assistant version, integration
  version, ESPHome version and the relevant log lines. Never publish passwords
  or API encryption keys.

## HACS publication status

The repository is structured for HACS and includes HACS and Hassfest validation
workflows. Version 0.1.0 has been tested on a real inverter installation. After
all repository checks pass, it can be submitted to the HACS default repository
list.

## License

MIT

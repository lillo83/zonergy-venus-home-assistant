# Zonergy Venus for Home Assistant

Custom integration for **Zonergy Venus hybrid inverters**. It supports a local
ESP8266/ESPHome RS485 gateway, a local ESP32 Bluetooth gateway for the original
Zonergy Wi-Fi dongle, or the same cloud service used by the official app.

> [!IMPORTANT]
> Version 0.3.0 adds charging from the grid on demand through the ESP8266
> RS485 gateway (see [Grid charging on demand](#grid-charging-on-demand)).
> Its switches, numbers and selector write real values to the inverter, so use
> them only if their meaning and limits match your inverter model.

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
- charging from the grid on demand, with duration, and the inverter operating
  mode (self-consumption / TOU)
- charge and discharge periods currently stored in the inverter

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

## Installation through HACS

If **Zonergy Venus** does not appear when you search for it in HACS, the
repository is not in the HACS default list yet; add it as a custom repository
first (steps 1 to 3). Otherwise start from step 4.

1. In HACS open the menu in the upper-right corner and choose
   **Custom repositories**.
2. Add this URL:

   `https://github.com/lillo83/zonergy-venus-home-assistant`

3. Select type **Integration** and press **Add**.
4. Search for **Zonergy Venus** in HACS.
5. Open it and press **Download**.
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
counters about once per minute. A self-healing watchdog rebuilds the Bluetooth
connection after 90 seconds without inverter packets and restarts the ESP32
only if data still does not resume.

### BLE battery SOC (0.2.0 and later)

The existing **Zonergy BLE Stato di Carica Batteria** entity reports the mean
SOC supplied by register `3006`; its name is preserved. The BLE firmware now
reads five words starting at `3004` and adds:

| Entity | Source | Unit |
|---|---|---|
| Zonergy BLE SOC Batteria Max | Register 3007 | % |
| Zonergy BLE SOC Batteria Min | Register 3008 | % |
| Zonergy BLE Delta SOC Batterie | Maximum minus minimum SOC | percentage points, displayed as % |

Maximum and minimum describe the battery modules as a group, not fixed battery
numbers. A maximum of 90% and a minimum of 85% gives a delta of 5 percentage
points. Short replies or invalid ranges leave these three values unknown.
The integration discovers them automatically from the updated firmware.

**Updating through HACS does not flash the ESP32.** To obtain these values:

1. Update the integration to `v0.2.0` or later and restart Home Assistant.
2. Update the BLE node using
   [`esphome/zonergy-venus-esp32-ble.yaml`](esphome/zonergy-venus-esp32-ble.yaml),
   retaining your node name, Wi-Fi/API settings and personal secrets.
3. Run **Validate** in ESPHome before installing the firmware.
4. Install the firmware, then reload the Zonergy Venus integration so it
   discovers the new entities. For a node managed by the standard ESPHome
   integration, check its device page for the new sensors.

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

> [!WARNING]
> The write controls below exist only in ESPHome RS485 mode and have **not
> been tested yet** on a real inverter. Only reading has been verified. There is also no timeout or failsafe: a
> value written to the inverter stays there until something writes a different
> one, even if Home Assistant or the gateway goes offline. Use these controls
> at your own risk and check the result on the inverter display or official app.

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

## Grid charging on demand

The ESP8266 firmware can charge the battery from the grid whenever you want,
without editing time slots in the Zonergy app:

1. set `Durata Carica da Rete` (0.5-8 hours) and `Potenza Carica Forzata`
   (the charging power, register 2957)
2. turn on `Carica Batteria da Rete`

The ESP8266 writes a charge window from the current time for the chosen
duration, puts the inverter in TOU mode and, when the time is up or the switch
is turned off, puts it back in self-consumption. If the ESP8266 restarts during
a charge, it restores self-consumption at boot. `Esito Scrittura Fasce`
reports whether the periods were really written.

Requirements and limits:

- `Abilitazione rete elettrica` (grid charging) must be enabled in the Zonergy
  app; this setting is not yet controlled by the ESP8266
- on the tested inverter only period 1 is written; keep period 2 in the app
  outside the hours you charge on demand, for example charge 00:00-06:00 and
  discharge 22:00-23:59
- choose a charging power that your grid connection can supply together with
  the house load

Registers used, all on Modbus address 1:

| Register | Access | Meaning |
|---|---|---|
| 2300 | write (function 6) | Operating mode: 0 = self-consumption, 1 = TOU |
| 2728-2735 | read (function 4), write (function 16) | Period 1: charge start, charge end, discharge start, discharge end; two registers per time (hours, minutes), each as two ASCII digits, e.g. `0x3031` = `01` |
| 2736-2743 | read (function 4) | Period 2, same layout |
| 2957 | write (function 6) | Charging power in W |

The inverter rejects reads of the control registers (2300, 2955, 2956, 2957,
2962), so these entities show the last value sent from Home Assistant, not a
value read back from the inverter.

### Controls-only firmware

If you already read the inverter with the ESP32 Bluetooth firmware, flash
[`esphome/zonergy-venus-esp8266-controlli.yaml`](esphome/zonergy-venus-esp8266-controlli.yaml)
on the ESP8266 instead of the full firmware. It keeps only the controls above
and the charge periods, so the RS485 bus, shared with the original Wi-Fi
dongle, carries much less traffic. Use it with the native ESPHome integration:
it does not expose the measurements that the Zonergy Venus integration uses to
recognize an RS485 gateway.

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

## Validation and releases

Every push, and a daily scheduled run, validates the repository with the HACS
action and Hassfest. A separate workflow imports the integration against the
latest Home Assistant release to catch breaking changes early. A release is
published automatically when a new version in `manifest.json` reaches `main`
and validation passes.

Reading is tested on a real installation with a Zonergy Venus6000-S1
inverter. On the same inverter, `Carica Batteria da Rete`, `Modalità Inverter`
and `Potenza Carica Forzata` have been tested; `Forza Carica Batteria`,
`Limite Carica da Rete` and `Sorgente Carica: Rete + PV` have not.

## License

MIT

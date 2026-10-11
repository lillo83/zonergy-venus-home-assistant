# PV export with battery SOC preservation — research (no device writes)

## Desired behavior
- Continue powering home loads from PV when available.
- Export remaining PV production to the grid on demand.
- Do not intentionally charge or discharge the batteries; keep current SOC as closely as possible.
- Return safely to the prior Self Consumption configuration.
- Preserve the working ESP32 BLE read-only firmware and existing Home Assistant entities.

## Findings
1. Official Venus 3680–6000-S1 user manual describes TOU mode with a PV surplus setting: prioritize supplying the grid; outside defined discharge periods, the battery should not discharge and the grid supplies loads if PV is insufficient. **It does not establish that battery charging stops entirely**.
2. Official manual warns that the full feed-in mode may discharge batteries to maintain grid output. **Do not use full feed-in as a battery-preserving shortcut.**
3. Official app exposes Self Consumption, TOU, Feed-in, Remote Mode; the user's Remote Mode selection was not confirmed/applied.
4. Existing `custom_components/zonergy_venus/cloud_api.py` implements authentication and read-only `/dsweb/param/readDeviceData`; **no cloud write endpoint is currently validated**.
5. Existing BLE path is read-only and should not be changed during investigation.

## Required evidence before implementation
- Identify exact setting/register for work mode and PV surplus priority, with verified value mapping for this firmware.
- Determine whether charge and discharge can each be independently prevented; no guessed register values or write endpoints.
- Confirm effect on house loads, export, grid imports, SOC and BMS using passive measurements.
- Check grid/export limits and installation permissions.
- Define timeout, state verification, failure recovery, and original-setting restoration.
- Test against mocked payloads before any live writes; enable live controls only by explicit opt-in.

## Implementation gate
No switches, automations, cloud write requests, or BLE firmware changes until verified documentation/protocol and user-approved test procedure.

## Sources
- Official manual listing: https://www.zonergy.com/it/scaricare/manuale-utente-venus-ita-20230705/
- English manual transcription (TOU and full feed-in behaviors): https://www.scribd.com/document/631811477/Venus-User-Manual-EN
- Integration cloud API: https://github.com/lillo83/zonergy-venus-home-assistant/blob/main/custom_components/zonergy_venus/cloud_api.py

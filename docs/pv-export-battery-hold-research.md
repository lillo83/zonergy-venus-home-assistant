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

## Evidence from app screenshots (October 2026)
- TOU enables **Excess PV production** picker: **Battery charge** vs **Grid connection**; **Grid connection** was already selected in the unconfirmed TOU editor.
- Charge source picker: **Grid and PV** vs **PV**; Grid and PV selected in the unconfirmed editor.
- Charge power field: current 500, permitted 100–5000 (UI erroneously labels percentages); **zero is not accepted**. This parameter cannot be used as a verified charge-off switch.
- Two sets of charging and discharging time windows visible (defaults 01:00–03:00 charging, 18:00–23:00 discharging); do not assume these schedules are active in Self Consumption.
- User only selected TOU and Remote Mode locally in the editor; **never pressed Confirm**, so there is no evidence the live inverter work mode changed.

## Manual behavioral nuance
The Venus manual describes TOU grid-first surplus as: PV serves load first, excess feeds grid first, with any excess above the inverter's output capacity potentially charging batteries. Outside discharge windows, battery is not discharged; grid supplies shortfall. Thus **grid-first does not imply charge inhibition or absolute SOC hold**.

## Safe next steps
1. Obtain firmware-specific work-mode, TOU PV-surplus-priority and schedule register mapping from Zonergy documentation/support or read-only authenticated API responses; do not guess values.
2. Read-only inspection of settings and compare with app (no save) and inverter LCD.
3. If evidence establishes a safe reversible procedure, request user consent for a short attended TOU test, logging PV, house load, grid export/import, battery watts and SOC before/during/after, with immediate return to Self Consumption.
4. Do not claim a 'hold battery SOC' control until charge **and** discharge inhibition are independently proven; if not possible, offer clearly named 'Grid-first surplus (battery may still charge)' instead.

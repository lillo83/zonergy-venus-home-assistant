## Novità

- mantenuto il SOC medio nella stessa entità BLE già esistente
- aggiunti SOC massimo, SOC minimo e differenza tra i moduli batteria
- estesa la lettura BLE ai cinque registri 3004–3008
- valori nuovi non disponibili se la risposta è incompleta o fuori intervallo
- aggiornati README, changelog e versione del firmware

## Aggiornamento

L'aggiornamento da HACS non modifica automaticamente il firmware ESP32.
Per ottenere i nuovi sensori, aggiorna anche
`esphome/zonergy-venus-esp32-ble.yaml`, mantenendo nome del nodo, impostazioni
Wi-Fi/API e i tuoi valori in `secrets.yaml`.
Esegui **Convalida** prima di installare il firmware, poi ricarica
l'integrazione Zonergy Venus per rilevare le nuove entità.

Il SOC massimo e minimo rappresentano gli estremi tra i moduli, non batterie
con numero fisso. Il delta è espresso in punti percentuali: 90% meno 85% = 5.

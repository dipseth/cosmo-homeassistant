<p align="center">
  <img src="custom_components/cosmo/brand/icon@2x.png" alt="COSMO" width="128" height="128">
</p>

# COSMO Watch for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

Bring the [COSMO JrTrack](https://cosmotogether.com) kids smartwatch into Home Assistant. Sign in
with your COSMO: Mission Control parent account and every watch on it becomes a device: live GPS
location, battery, last-fix time, and emergency status, with buttons to locate or ring the watch.
Read-only for location; the only writes are the optional **Locate now** and **Ring watch** buttons.

COSMO runs on the myFilip platform, so this talks to `api.myfilip.com` with your parent login.

## Features

- **device_tracker** with the watch's GPS position and accuracy, so it shows on the map and in zones
- **Battery**, **Last fix**, **GPS source** (GPS/LBS/WiFi) and **Phone number** sensors
- **Emergency** and **Powered off** binary sensors for automations
- **Locate now** button (asks the watch for a fresh fix) and **Ring watch** button (find my watch)
- One HA device per watch; multiple watches on one account are supported
- Re-authentication prompt if the password changes; the location poll interval is adjustable

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/dipseth/cosmo-homeassistant`, type *Integration*
2. Install **COSMO Watch** and restart Home Assistant
3. **Settings → Devices & services → Add integration → COSMO Watch** and sign in with your
   COSMO parent email and password

### Manual

Copy `custom_components/cosmo` into your Home Assistant `config/custom_components/` folder and
restart. `install.sh` does this over SSH (`./install.sh` uses the `homeassistant` entry in your
`~/.ssh/config`).

## Entities

One device per watch, named after the child:

| Entity | Type | Notes |
|---|---|---|
| **Location** | device_tracker | GPS lat/long + accuracy; attributes: GPS source, last fix, phone number |
| **Battery** | sensor (battery %) | watch battery |
| **Charger battery** | sensor (battery %) | charging-case/cradle level (disabled by default) |
| **Last fix** | sensor (timestamp) | when the current fix was taken |
| **GPS source** | sensor | GPS, LBS (cell), or WiFi |
| **Phone number** | sensor (diagnostic) | the watch's line |
| **Firmware / IMEI** | sensor (diagnostic) | disabled by default |
| **Emergency** | binary sensor (safety) | SOS / emergency mode active |
| **Powered off** | binary sensor (problem) | the watch reported shutdown |
| **Locate now** | button | ask the watch for a fresh fix |
| **Ring watch** | button | ring the watch (find my watch) |

## How it works

`GET v2/map` on the myFilip API returns every watch on the account with its current location,
battery and fix time in one call; the integration polls it (default every 60s) and maps each watch
to a device. Login is `POST v2/token` with your email, password and the COSMO white-label id, and
the access token is refreshed automatically.

## Notes

- Your password is stored in the config entry (as with any cloud integration) and sent over HTTPS.
- Nothing on your COSMO account is changed except when you press **Locate now** or **Ring watch**.
- This is an unofficial integration, not affiliated with COSMO or myFilip.

## License

MIT © 2026 Seth Rivers

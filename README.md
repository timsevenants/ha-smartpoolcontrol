# Smart Pool Control – Home Assistant integration

Unofficial Home Assistant custom integration for pools managed through the
**Smart Pool Control** owner portal (`owner.smartpoolcontrol.eu`), by Europe
Pool Supplies B.V.

The portal has no public API, so this integration logs in with your owner
credentials, keeps a session and scrapes the measurements page / submits the
existing web forms. It is **not affiliated with or endorsed by** Europe Pool
Supplies / Smart Pool Control.

> ⚠️ **Pool cover safety.** The cover entity can open and close the pool deck
> remotely. The web portal only lets you do this when your phone is within
> 100 m and warns that you must have *direct line of sight* of the cover.
> Home Assistant cannot verify either. The cover entity is therefore
> **disabled by default**. Only enable and automate it if you have another
> reliable way to guarantee the pool area is clear. Use at your own risk.

## Features

### Sensors
- pH (and pH target)
- Redox / ORP "Rx" in mV (and target)
- Water temperature (and target)
- Outside temperature
- Solar temperature (if your installation has the sensor)
- Pump speed (off / low / medium / high / maximum)
- Cover state (open / closed)

### Binary sensors
- Heating on/off
- Pool online/offline (connectivity)

### Controls
- **Numbers:** pH target (6.8–7.6), Redox target (0–999 mV), water temperature target
- **Switches:** lighting, frost protection, pump force-on
- **Selects:** pump speed (filter schedule 1), lighting program (9 modes)
- **Cover:** open / close / stop the pool deck *(disabled by default — see warning above)*

## Installation

### HACS (custom repository)
1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/sevenants/ha-smartpoolcontrol`, category *Integration*.
3. Install **Smart Pool Control**, then restart Home Assistant.

### Manual
Copy `custom_components/smartpoolcontrol` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration
*Settings → Devices & Services → Add Integration → Smart Pool Control* and
enter the same e-mail and password you use on the portal. The pool is
discovered automatically.

## How it works (reverse-engineering notes)
The portal is a Django app. The integration:
1. `GET /login/` to read the CSRF token, then `POST /login/`
   (`csrfmiddlewaretoken`, `username`, `password`) with a matching `Referer`.
2. `GET /` redirects to `/pools/measurements/<pool_id>/` → that's how the pool
   id is discovered.
3. Status is parsed from `/pools/measurements/<pool_id>/`.
4. Controls map to the portal's own endpoints/forms:
   - Lighting toggle: `GET /pools/lighting_toggle/<id>/`
   - Cover: `GET /pools/settings/<id>/deck_open|deck_close|deck_stop`
   - Setpoints/options: `POST /pools/settings/<id>/{ph,rx,temperaturegeneral,filtergeneral,filterschedule1,lighting}`
     (the integration re-submits the full Django formset, only changing the
     relevant field).

Because it scrapes HTML, a portal redesign may break parsing. `scripts/probe.sh`
helps re-inspect the structure (read-only).

## Disclaimer
Provided "as is", without warranty. Automating pool chemistry, heating and
especially the cover carries real-world risk. You are responsible for safe and
lawful operation of your pool.

## License
MIT — see [LICENSE](LICENSE).

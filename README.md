# Smart Pool Connect – Home Assistant integration

Unofficial Home Assistant custom integration for pools managed through
**Smart Pool Connect** (`smartpoolconnect.eu`), by Europe Pool Supplies B.V.

The vendor decommissioned the old `owner.smartpoolcontrol.eu` owner portal and
moved to a modern REST API at `api.smartpoolconnect.eu`. This integration talks
to that API using an **API key** you generate in the web portal. It is **not
affiliated with or endorsed by** Europe Pool Supplies / Smart Pool Connect.

> ⚠️ **Pool cover safety.** This integration deliberately **does not** move the
> pool cover/deck. The API can open/close the deck (`POST /pool/{pid}/cmd/…`),
> but a moving cover can trap a person or animal and cannot be observed from
> Home Assistant — the vendor's own app enforces a "within 100 m, direct line
> of sight" rule for this reason. The cover is exposed **read-only** as a
> diagnostic status sensor only.

## Features

### Sensors
- pH (and pH target)
- Redox / ORP "Rx" in mV (and target)
- Water temperature (and target)
- Outside / ambient temperature
- Solar temperature (if your installation has the sensor)
- Pump speed (off / low / medium / high)
- Cover status (diagnostic, raw code — read-only)

### Binary sensors
- Pool online / offline (connectivity)
- Pump running

### Controls
- **Numbers:** pH target (6.8–7.6), Redox target (0–999 mV), water temperature target
- **Switches:** lighting, frost protection, pump force-on
- **Select:** pump speed (off / low / medium / high)

## Installation

### HACS (custom repository)
1. HACS → ⋮ → *Custom repositories*.
2. Add `https://github.com/timsevenants/ha-smartpoolcontrol`, category *Integration*.
3. Install **Smart Pool Connect**, then restart Home Assistant.

### Manual
Copy `custom_components/smartpoolcontrol` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration
1. In the Smart Pool Connect web portal, open **API Keys** and generate a key
   (it starts with `spc_`).
2. *Settings → Devices & Services → Add Integration → Smart Pool Connect* and
   paste the API key. If the key grants access to more than one pool you'll be
   asked which one; otherwise the pool is added automatically.

## How it works
The integration polls `GET /pool/{pid}` every couple of minutes and parses each
module (`ph`, `cl`, `filter`, `lighting`, `cover`, `temperature`). Control is a
`PATCH /pool/{pid}/{module}` carrying only the changed field(s) at the top level
(there is no `config` envelope). The exact payloads were confirmed against the
live API:

| Action | Endpoint | Body |
| --- | --- | --- |
| pH / water target | `PATCH …/ph`, `…/temperature` | `{"target": <v>}` |
| Redox target | `PATCH …/cl` | `{"target": <v>}` (flat; reads back at `config.rx.target`) |
| Frost protection | `PATCH …/temperature` | `{"frost_protection": <bool>, "target": <current>}` |
| Lighting on/off | `PATCH …/lighting` | `{"always_active": <bool>}` |
| Pump force / speed | `PATCH …/filter` | the whole `filter.config` struct, one field changed |

Momentary actions (cover open/stop/close, backwash, shock, lighting cycle) live
under `POST /pool/{pid}/cmd/{command}`; only the safe, non-cover ones would ever
be considered. `scripts/probe.sh` performs read-only `GET`s for debugging.

## Disclaimer
Provided "as is", without warranty. Automating pool chemistry and heating
carries real-world risk. You are responsible for safe and lawful operation of
your pool.

## License
MIT — see [LICENSE](LICENSE).

# ⚠️ WARNING: USE AT YOUR OWN RISK ⚠️

**IMPORTANT SAFETY NOTICE:** This integration allows you to read and **write settings** to your Midnite Solar MPPT charge controller. Incorrect configuration can result in:
- Damage to your MPPT charge controller
- Damage to your battery bank
- Overcharging or undercharging of batteries
- Potential fire hazard

**You are solely responsible for any consequences that may result from using this integration.** The authors and contributors accept no liability for any damage, loss, or injury caused by the use of this software.

**Always verify your settings before applying them to your charge controller.**

---

# Midnite Solar Integration for Home Assistant

Support for Midnite Solar Classic charge controllers over Modbus TCP (via its built-in Ethernet module), including the private commands the official Midnite Solar AIR
desktop app uses: set the Classic's clock, reboot it, and the enable-flag
toggles from its Features panel.

## What you get

About 150 entities per Classic (exact counts are pinned by the test suite):

### Sensors (47)
Battery voltage, PV voltage, output current, watts, charge stage and internal
state, battery/FET/PCB temperatures, daily and lifetime kWh and Ah, float time
today, last-measured Voc, why the Classic went to rest, the unit name, MAC and
IP addresses, the Classic's firmware (app/net version and build revisions) —
and **Classic Date / Classic Time**: the Classic's own wall clock, read from
the same registers (4214-4217) the AIR app reads.

### Binary sensors (27)
One per Info Flag bit (Table 4130-1): charge in progress, equalizing, ground /
arc faults, aux 1/2 state, battery temperature sensor installed, and
**Ethernet Writes Locked** (the Classic ignores setting writes until the serial
number is sent — this integration does that for you automatically).

### Buttons (7)
- **Save to EEPROM now** — commit every pending (EE) setting in one write
- **Discard Unsaved Settings** — re-read the EEPROM (undo pending changes)
- **Reset Info Flags**
- **Force Sweep** — force an MPPT sweep
- **Reset Faults**
- **Set Classic Clock** — write this machine's local time to the Classic's
  clock (the AIR app's private function-105 file write; read the note below)
- **Reboot Classic** (disabled by default) — the AIR app's two-write reboot:
  enable the "Night Auto Reset" flag, then raise ForceNite. The Classic drops
  the connection and comes back.

### Switches (8)
- **Auto Save EEPROM** (off by default) — when on, every setting change is
  committed to EEPROM automatically; when off, changes apply immediately but
  you commit deliberately with "Save to EEPROM now". (Bench observation: this
  firmware also appears to persist on its own at times — commit to be sure.)
- **Seven enable-flag toggles** from the AIR app's Features panel: Ground
  Fault Protection and Arc Fault Detection (Enable Flags 1), and Night Auto
  Reset, Networked Battery Sensor, Low-Max Mode, Insomnia Mode and Keep
  Logging at Night (Enable Flags 2). Each is a read-modify-write that touches
  only its own bit, and only its own bit is verified — the registers pack many
  settings together.

### Numbers (60), Selects (7), Text (1)
Set-points the register map exposes: absorb/float/equalize voltages, current
limits, absorb/equalize times and intervals, temperature-compensation
voltages, aux 1/2 threshold voltages, MPPT parameters, Modbus port/address...
Selects for battery type, MPPT mode, aux 1/2 functions and modes, and
**Nominal Battery Voltage** (the register holds the bank volts itself: 48
means a 48 V bank). The text entity sets the unit name (up to 8 characters).

## The Classic's clock — know before you press the button

The AIR app's "write time" command works over Modbus — and **the Classic's Ethernet port card
owns the time**. On our bench unit both the official app's write and this
integration's write landed and ran at correct rate for ~30 s, then the card
re-published its own timezone-shifted time and the clock snapped back. Fixing
the card's clock/timezone (via its cloud config) is the real fix; setting the
clock at the Classic's LCD persists. Until the card is sorted, treat **Set
Classic Clock** as best-effort — it does write, it may not hold. (Details:
FINDINGS section 40, air-app-reverse/PROTOCOL.md section 4.2.)

## One connection at a time

The Classic's Ethernet port serves **one Modbus TCP connection at a time**:
while one is open, a second connection attempt fails and the existing
connection keeps working untouched (bench-corrected 2026-09-24 - the older
docs here said "latest-wins"; it is not). Keep other tools (scripts, a
second Home Assistant) off the Classic while this integration polls - or
let them not touch it at all: the bridge API below serves the same data to
anything else through Home Assistant, and this integration's config entry
can be disabled to hand the one connection to another client.

## The bridge API (desktop apps, dashboards, scripts)

Because only one Modbus client can hold the Classic, the integration can act
as that one client *for* everything else: enable **Enable bridge API** in the
integration's options and it serves a small JSON API on Home Assistant's own
HTTP port. Nothing else ever needs to touch the Classic's Ethernet port.

- Off by default, and every call needs a Home Assistant access token like
  any other `/api` call: create a **long-lived access token** on your
  profile page and send it as `Authorization: Bearer <token>`.
- A desktop app finds the bridge by itself. The integration advertises the
  mDNS service `_midnite-bridge._tcp.local.` and - because HAOS's firewall
  drops inbound 5353 and Apple's responder shares that port and
  load-balances answers away from any raw client - it *also* beats a UDP
  beacon on port 4627 every five seconds carrying the same facts (address,
  port, API version, entry id, the Classic's address) plus unit name and
  model. The beacon is inbound-to-client, which no firewall blocks, so it
  works identically on macOS, Linux, Windows, Android and iOS; mDNS stays
  as the bonus for networks where it works.

With entry id `ENTRY` (visible in the integration's URL):

| Call | What it does |
|---|---|
| `GET /api/midnite/ENTRY/state` | the last poll: raw registers by group, register-name table, unit name/MAC/model/serial, the Classic's clock and firmware, the EEPROM commit mode. No Modbus traffic - poll it as often as you like |
| `POST /api/midnite/ENTRY/write` | `{"register": name-or-number, "value": int, "commit": bool}` - the same write-with-read-back-check the entities do; `commit: true` also sends ForceEEpromUpdate for this write |
| `POST /api/midnite/ENTRY/clock` | `{"time": "ISO 8601"}` - the AIR app's private file-write; seconds and weekday are not settable, and the Classic's Ethernet port may republish its own time minutes later (see FINDINGS) |
| `POST /api/midnite/ENTRY/reboot` | the app's "Bully Menu"; the Classic drops the connection as it restarts |
| `POST /api/midnite/ENTRY/save` | "Save to EEPROM now": one ForceEEpromUpdate committing every pending (EE) setting at once - the same button Home Assistant's UI has; never a side effect of reading |
| `GET /api/midnite/ENTRY/datalogger` | the last swept days from the Classic's own datalogger |
| `POST /api/midnite/ENTRY/datalogger/refresh` | reads its whole stored year (96 paced private reads on the shared connection - takes seconds) |

Register values are the RAW integers the register map scales by tenths -
the client divides, exactly like the AIR app's own conversions. Some
registers are refused outright: the unlock registers 20492/20493 (they are
the Modbus handshake itself), the app's "untouchables", and the whole
the Classic's Ethernet port network block - a write there would move the very address the
client is calling.

## Installation

1. Copy `custom_components/midnite_solar` into your Home Assistant `config`
   directory
2. Restart Home Assistant
3. Add the integration via the UI

### UI Setup (Recommended)
1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration** and search for "Midnite Solar"
3. Enter the Classic's IP address and port (default 502) and the update
   interval (default 15 s)

The integration claims the device by its MAC address, so DHCP discovery finds
it without typing an address.

## Requirements

- A Midnite Solar Classic with a the Classic's Ethernet port (or equivalent Modbus TCP path)
- Network connectivity to the Classic; port 502 open between HA and the device
- Python 3.13+ / pymodbus 3.15 (managed by the integration's manifest)

## Technical notes

- **Wire unit id is always 1** on the socket; the Classic's Ethernet port ignores it. The
  Classic's own Modbus address (4326) is for its serial/other Modbus ports.
- **Ethernet write-protect:** the Classic ignores setting writes until its
  serial number is written to the unlock registers (20492/20493). The
  integration reads the serial (28673/28674) and re-sends the unlock after
  every (re)connect; the "Ethernet Writes Locked" binary sensor reports the
  lock state itself.
- **EEPROM commits are yours to make:** a set-point write applies immediately;
  the ForceEEpromUpdate commit writes *every* pending (EE) register at once,
  so it happens only via the "Auto Save EEPROM" switch or its button.
- **Register truth:** every scale, word order and bit position is from the
  official register map PDF (and, where the map self-contradicts, the
  documented bench findings — see FINDINGS.md in the parent workspace).

## Safety notes

- Changing voltage setpoints can affect battery health and lifespan
- Always consult your battery manufacturer's specifications
- The integration provides direct access to device settings - use with caution
- Some operations (arc-fault settings, reboots) only take effect after a
  Classic restart

## License

This integration is open-source software licensed under the MIT License.

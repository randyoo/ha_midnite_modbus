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

Support for Midnite Solar Classic charge controllers over Modbus TCP (WIFI175 /
Ethernet module), including the private commands the official Midnite Solar AIR
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

The AIR app's "write time" command works over Modbus — and **the WIFI175 card
owns the time**. On our bench unit both the official app's write and this
integration's write landed and ran at correct rate for ~30 s, then the card
re-published its own timezone-shifted time and the clock snapped back. Fixing
the card's clock/timezone (via its cloud config) is the real fix; setting the
clock at the Classic's LCD persists. Until the card is sorted, treat **Set
Classic Clock** as best-effort — it does write, it may not hold. (Details:
FINDINGS section 40, air-app-reverse/PROTOCOL.md section 4.2.)

## One connection at a time

The WIFI175 accepts extra TCP connections but its Modbus bridge is
latest-wins: only one polling client can use it cleanly. Keep other tools
(the AIR app, scripts, a second Home Assistant) off the Classic while this
integration polls.

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

- A Midnite Solar Classic with a WIFI175 (or equivalent Modbus TCP path)
- Network connectivity to the Classic; port 502 open between HA and the device
- Python 3.13+ / pymodbus 3.15 (managed by the integration's manifest)

## Technical notes

- **Wire unit id is always 1** on the socket; the WIFI175 ignores it. The
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

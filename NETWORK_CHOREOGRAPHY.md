# The Ethernet card's write choreography (why the bridge opens this door only as a door, not a hose)

Status: **design record for the /network bridge endpoint** (2026-09-26).
Bench ground truth: `/Users/randy/midnite/FINDINGS.md` §53 (+ round 2/3/4
addenda + the live app verification). Nothing in this file is theory: every
rule below was bought with writes to the real Classic 250 on the bench
(10.10.10.77), with the user's physical fallback ("walk out and switch it
back to DHCP").

## The hardware's actual behaviour

The Classic's Ethernet card (the Angstrom-era board behind the RJ45) accepts
writes to its own settings block, registers 20481-20491:

| reg  | meaning                       | frame rule (enforced, see below)       |
|------|-------------------------------|----------------------------------------|
|20481 | settings word (bit 0 DHCP, bit 1 web access) | only as the 3-word combo with its IP |
|20482/83 | static IP (reversed-octet pair)        | count-2 pair, or inside the combo |
|20484/85 | gateway                                | count-2 pair                  |
|20486/87 | netmask                                | count-2 pair                  |
|20488/89 | DNS 1                                  | count-2 pair                  |
|20490/91 | DNS 2                                  | count-2 pair                  |
|20492/93 | the serial unlock pair                 | NEVER the network door (hub-owned) |
|20494+  | malformed non-Modbus private surface   | never touched by anything      |

Behaviour, measured:

1. **Every write APPLIES, and the apply kills the connection.** Any write
   to the block - even a same-value write - makes the card reprogram its
   network a moment after the ack: the ack arrives, the line is dropped
   ~0.4 s later, a fresh connection is healthy inside a second. The apply
   can also fire *mid-write* (round 2: the second word of a pair died
   mid-transaction).
2. **The ack proves nothing.** Round 2's pair, written word by word, was
   caught by the apply between the words; the read-back then showed
   `0.0.88.44` - a half-applied DNS. A value only exists once a read-back
   says so.
3. **20481 bit 1 (web access) is READ-ONLY over Modbus** on this firmware
   (every apply rewrote the word to `0x0000` after we wrote `0x0002`
   twice). The Flutter app must not offer it, and this integration must
   not pretend a flags write can bring the card's web UI back. The card's
   own config surface (the private 20494+ frames) is the standing suspect
   for owning it.
4. **Going static on a card whose static copy reads zero cuts it off.**
   This bench survived only because the DHCP lease is echoed into the
   static registers - the static copy already read 10.10.10.77/255.255.255.0
   before the DHCP bit was cleared. A virgin card would boot dead.
5. Going DHCP the other way may give the card a **new address** from the
   router - the session then ends and the card is found by its new number.
   That is honest, not a bug.

## The choreography (exactly one function does this, on both transports)

```
unlock (the serial into 20492/93, per-socket grant)
  ↓
ONE atomic func-16 frame        ← never two func-6s, never a count-1
  ↓                              write to this block
expect silence, not an ack       ← a connection-level raise is allowed
  ↓                              here: the apply may fire mid-frame
wait ~0.6 s
  ↓
read the written words back      ← reconnect + re-unlock happen here
  ↺ up to ~20 times              (read_holding/ensure_unlocked do it)
  ↓
MATCH → done. NO MATCH EVER → it did not land - say so honestly.
```

The read-back is the ONLY verdict. The Flutter transport does exactly this
(`DirectClassicSource.writeNetwork`, wire-verified live against the card
2026-09-26); the integration does the same through `MidniteHub.write_network`
so Home Assistant's own always-on connection gets the identical care.

## The frame rules, and why they are enforced HERE rather than in clients

- The settings word may only ride its **3-word combo** `[flags, ip-low,
  ip-high]` starting at 20481 (round 4 proved it as the safest single
  operation for a DHCP change: the static IP lands in the same atomic
  write that turns DHCP off, so the address cannot move under you).
- Every other value is exactly **one count-2 pair** at its even start.
- A count-1 write to any of 20481-20491 is **refused**: every write to this
  block applies, so a lone word is a guaranteed half-frame waiting to
  happen. This is the single rule that makes the block safe enough to open
  at all.
- Clearing the DHCP bit additionally requires a sane static copy - the IP
  in the frame nonzero AND the netmask currently read nonzero - and the
  hub REFUSES the combo otherwise. A client can ask; the hardware-facing
  layer decides.
- 20492/93 and everything ≥20494 are not writable through this door by
  any caller, ever.

## Why the old refusal stays for /write

`BRIDGE_FORBIDDEN_WRITES` keeps this block sealed on the ordinary
single-register `/write` path **forever**: that path writes one word, and
one word to this block is exactly the half-frame hazard. `/network` is not
a loosening of the ban - it is a different operation, with atomic frames
and a read-back verdict, gated on the same write PIN as every other
mutating call.

## What Home Assistant itself feels

HA holds the Classic's ONE Modbus TCP connection. During a /network write
the card drops that connection as it applies. The hub's existing
reconnect + re-unlock machinery (the same that survives the Classic's own
reboot quirks) rejoins it inside a second; meanwhile coordinator polls
fail and the integration looks briefly offline, which is the truth: the
card is reprogramming. The /network POST itself blocks (executor job) only
until the read-back confirms - typically ~1-2 s, bounded by the confirm
budget (~12 s), after which it says plainly that the card never read back.

Two operator-visible notes, stated by the endpoint, not hidden:
- DHCP ON: "the card may take a new address from the router - if it drops
  off this session, find it by its new number".
- DHCP OFF: the static-copy sanity is checked before the frame leaves.

## Test doctrine

The hardware-free suite simulates all of it on a scripted pymodbus client
double: ack-then-drop, mid-frame raise with the frame still landing (the
read-back must confirm), a clamping client whose read-back never matches
(the endpoint must fail honestly), the count-1 refusal, the dead-static
refusal, and the PIN gate. No test may ever open a socket (suite rule);
the wire behaviour lives here and in FINDINGS 53, where it was bought.

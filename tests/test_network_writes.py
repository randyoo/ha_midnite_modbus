"""The Ethernet card's door: /network and the FINDINGS 53 choreography.

The card APPLIES every write to its settings block by reprogramming its
network - and the apply kills the Modbus connection, sometimes between the
words (the bench read back a half-applied DNS of 0.0.88.44). So the door
takes ONLY atomic frames and the READ-BACK is the only verdict; the ack
proves nothing. All of it is simulated here on a scripted client double -
the suite never opens a socket (suite rule); the wire truth is in
NETWORK_CHOREOGRAPHY.md and FINDINGS 53, where it was bought on the bench.
"""

from __future__ import annotations

from fakes import FakeApi
from midnite_solar import hub as hub_module
from midnite_solar.const import REGISTER_MAP
from midnite_solar.hub import MidniteHub
from pymodbus.exceptions import ConnectionException
import pytest
from test_bridge_api import installed, post

SETTINGS = REGISTER_MAP["IP_SETTINGS_FLAGS"]  # 20481
IP_LO = REGISTER_MAP["IP_ADDRESS_LOW_WORD"]
MASK_LO = REGISTER_MAP["SUBNET_MASK_LOW_WORD"]
DNS1_LO = REGISTER_MAP["DNS_1_LOW_WORD"]

# the words of 10.10.10.77 (reversed octets: low register first, low byte first)
IP_WORDS = (0x0A0A, 0x4D0A)
MASK_WORDS = (0xFFFF, 0x00FF)


class Result:
    def __init__(self, registers=None, error=False):
        self.registers = registers or []
        self._error = error

    def isError(self):
        return self._error


class Card:
    """The card's own state - settings live in the card, not the connection.

    policies, all measured on the bench:
      stay-up        the rare mercy: ack, answer, nothing drops
      ack-then-drop  the usual way: ack, then the apply kills the line
      mid-frame      the apply fires WHILE the frame is away - once; the
                     frame landed in the card (the words are applied before
                     the raise; read-back must still confirm)
      die-before-apply-first  the line dies before the frame lands (once);
                     the retried frame is identical, so retrying is safe
      clamped        the card rewrites the words back on apply and answers
                     the old values forever - the door must fail honestly
    """

    current = None

    def __init__(self, registers=None, policy="ack-then-drop"):
        self.registers = dict(registers or {})
        self.policy = policy
        self.frames = []  # accepted func-16 frames: (wire start, values)
        self.connects = 0


class CardClient:
    """One Modbus TCP connection to the Card. The apply kills THIS one."""

    def __init__(self, host=None, port=None, timeout=None, retries=None, **kwargs):
        self.card = Card.current
        self.card.connects += 1
        self.alive = True

    def connect(self):
        return True

    def close(self):
        self.alive = False

    def is_socket_open(self):
        return self.alive

    def _alive(self):
        if not self.alive:
            raise ConnectionException(
                "Connection unexpectedly closed: [Errno 54] Connection reset"
            )

    def write_register(self, address=0, value=0, **kwargs):  # the unlock pair
        self._alive()
        self.card.registers[address] = value
        return Result()

    def write_registers(self, address=0, values=None, **kwargs):
        self._alive()
        if self.card.policy == "die-before-apply-first":
            self.card.policy = "stay-up"
            self.alive = False
            raise ConnectionException("Connection unexpectedly closed mid-frame")
        # the frame lands in the card...
        for i, value in enumerate(values):
            self.card.registers[address + i] = value
        self.card.frames.append((address, list(values)))
        # ...and now the apply does whatever the card feels like.
        if self.card.policy == "clamped":
            for i in range(len(values)):
                self.card.registers[address + i] = 0  # answers the old words
        if self.card.policy in ("ack-then-drop", "clamped"):
            self.alive = False
        elif self.card.policy == "mid-frame":
            # once: the apply fired between the words; a re-sent frame
            # gets its normal ack
            self.card.policy = "stay-up"
            self.alive = False
            raise ConnectionException(
                "Connection unexpectedly closed 0.001 seconds into the answer"
            )
        return Result()

    def read_holding_registers(self, address=0, count=1, **kwargs):
        self._alive()
        return Result(
            registers=[self.card.registers.get(address + i, 0) for i in range(count)]
        )


def make_card_hub(monkeypatch, card):
    Card.current = card
    monkeypatch.setattr(hub_module, "ModbusTcpClient", CardClient)
    monkeypatch.setattr(MidniteHub, "RECONNECT_DELAY", 0)
    monkeypatch.setattr(hub_module.time, "sleep", lambda seconds: None)
    hub = MidniteHub("10.10.10.77", 502)
    hub.set_serial_number(24680)  # a fake identity, the policy's serial
    return hub


class TestHubChoreography:
    def test_the_usual_way_frame_lands_card_drops_line_read_back_confirms(
        self, monkeypatch
    ):
        card = Card(policy="ack-then-drop")
        hub = make_card_hub(monkeypatch, card)
        back = hub.write_network(DNS1_LO, [0x0101, 0x0101], confirms=4)
        assert back == [0x0101, 0x0101]  # the READ-BACK is the verdict
        assert card.frames == [(DNS1_LO - 1, [0x0101, 0x0101])]  # one atomic frame
        assert card.connects >= 2  # rejoined after the apply

    def test_the_apply_fires_mid_frame_the_words_still_read_back(self, monkeypatch):
        # Round 2's shape: the write itself raises, but the frame landed in
        # the card before the line died. Choreography: survive the raise,
        # rejoin, and let the read-back decide.
        card = Card(policy="mid-frame")
        hub = make_card_hub(monkeypatch, card)
        back = hub.write_network(DNS1_LO, [0x0101, 0x0101], confirms=4)
        assert back == [0x0101, 0x0101]

    def test_a_frame_that_died_before_landing_is_re_sent_then_confirms(
        self, monkeypatch
    ):
        # Retrying the SAME frame is safe (idempotent): the first attempt
        # never reached the card, the second lands, the read-back confirms.
        card = Card(policy="die-before-apply-first")
        hub = make_card_hub(monkeypatch, card)
        back = hub.write_network(DNS1_LO, [0x0101, 0x0101], confirms=4)
        assert back == [0x0101, 0x0101]
        assert len(card.frames) == 1  # only the frame that landed counts

    def test_a_card_that_keeps_answering_the_old_words_says_so(self, monkeypatch):
        # The clamped card acks, rewrites the words back, and stays up on a
        # fresh connection answering the old values. The door must NOT call
        # that success - it fails with what it last read.
        card = Card(registers={DNS1_LO - 1: 0xA8C0}, policy="clamped")
        hub = make_card_hub(monkeypatch, card)
        with pytest.raises(OSError, match="never read back"):
            hub.write_network(DNS1_LO, [0x0101, 0x0101], confirms=3)

    @pytest.mark.parametrize(
        ("start", "values"),
        [
            (SETTINGS, [0x0001]),  # the settings word alone: never
            (SETTINGS, [0x0001, IP_WORDS[0]]),  # half a combo: never
            (IP_LO, [0x0101]),  # a lone word of a pair: never
            (IP_LO, [0x0101, 0x4D0A, 0x0000]),  # three words where two live
            (MASK_LO + 1, [0x00FF, 0x0000]),  # odd start: half a pair
            (REGISTER_MAP["DNS_2_LOW_WORD"], [0x0008, 0x0008, 0x0000]),  # past 20491
        ],
    )
    def test_lone_words_and_half_frames_are_refused_before_the_wire(
        self, monkeypatch, start, values
    ):
        card = Card()
        hub = make_card_hub(monkeypatch, card)
        with pytest.raises(ValueError, match="atomic frame"):
            hub.write_network(start, values)
        assert card.frames == []
        assert card.registers == {}  # not even the unlock left on the wire

    def test_going_static_on_a_dead_netmask_is_refused(self, monkeypatch):
        # A card that boots 0.0.0.0/0 cuts itself off; the hub says no
        # before the frame can do it, whatever the client asked for.
        card = Card(registers={SETTINGS - 1: 0x0001, MASK_LO - 1: 0x0000})
        hub = make_card_hub(monkeypatch, card)
        with pytest.raises(ValueError, match="netmask"):
            hub.write_network(SETTINGS, [0x0000, *IP_WORDS], confirms=3)
        assert card.frames == []

    def test_going_static_without_an_ip_in_the_frame_is_refused(self, monkeypatch):
        card = Card(registers={MASK_LO - 1: 0xFFFF})
        hub = make_card_hub(monkeypatch, card)
        with pytest.raises(ValueError, match="0.0.0.0"):
            hub.write_network(SETTINGS, [0x0000, 0x0000, 0x0000], confirms=3)
        assert card.frames == []

    def test_the_combo_lands_when_the_static_copy_is_bootable(self, monkeypatch):
        # The safe DHCP-off operation (round 4): flags+IP in ONE atomic
        # frame, the static copy already sane on the card.
        card = Card(
            registers={SETTINGS - 1: 0x0003, MASK_LO - 1: 0xFFFF},
            policy="ack-then-drop",
        )
        hub = make_card_hub(monkeypatch, card)
        back = hub.write_network(SETTINGS, [0x0002, *IP_WORDS], confirms=4)
        assert back == [0x0002, *IP_WORDS]
        assert card.frames == [(SETTINGS - 1, [0x0002, *IP_WORDS])]

    def test_going_dhcp_needs_no_static_copy(self, monkeypatch):
        # Turning DHCP ON is safe whatever the static registers read - the
        # router owns the address now.
        card = Card(policy="ack-then-drop")
        hub = make_card_hub(monkeypatch, card)
        back = hub.write_network(SETTINGS, [0x0003, 0x0000, 0x0000], confirms=4)
        assert back[0] == 0x0003


class TestNetworkDoorBridge:
    """The /network view's contract, on the FakeApi double."""

    @pytest.mark.parametrize("start", [20481, "ABSORB_SETPOINT_VOLTAGE", None])
    def test_the_door_speaks_only_its_names(self, start):
        hass, _ = installed()
        response = post(hass, "network", {"start": start, "values": [1, 1]})
        assert response.status == 400
        assert "names" in response.body["error"]

    @pytest.mark.parametrize("values", [None, [], [True, 1], [70000, 1], "1,1"])
    def test_the_frame_must_be_words(self, values):
        hass, _ = installed()
        response = post(hass, "network", {"start": "DNS_1_LOW_WORD", "values": values})
        assert response.status == 400

    def test_a_happy_pair_answers_with_the_read_back(self):
        api = FakeApi()
        hass, _ = installed(api=api)
        response = post(
            hass, "network", {"start": "DNS_1_LOW_WORD", "values": [0x0101, 0x0101]}
        )
        assert response.status == 200
        assert response.body == {
            "ok": True,
            "start": "DNS_1_LOW_WORD",
            "readback": [0x0101, 0x0101],
        }
        assert api.network_frames == [
            (REGISTER_MAP["DNS_1_LOW_WORD"], [0x0101, 0x0101])
        ]

    def test_the_dhcp_answer_says_the_card_may_move(self):
        hass, _ = installed()
        response = post(
            hass,
            "network",
            {"start": "IP_SETTINGS_FLAGS", "values": [0x0003, *IP_WORDS]},
        )
        assert response.status == 200
        assert "new address" in response.body["note"].lower()

    def test_the_hubs_honest_refusals_travel_verbatim(self):
        api = FakeApi()
        api.network_error = ValueError(
            "the card's static netmask reads 0.0.0.0 - going static on that "
            "cuts the card off; fill the netmask first"
        )
        hass, _ = installed(api=api)
        response = post(
            hass,
            "network",
            {"start": "IP_SETTINGS_FLAGS", "values": [0x0000, *IP_WORDS]},
        )
        assert response.status == 400
        assert "cuts the card off" in response.body["error"]

    def test_a_card_that_never_reads_back_is_refused_not_guessed(self):
        api = FakeApi()
        api.network_error = OSError("the Ethernet card never read back the frame")
        hass, _ = installed(api=api)
        response = post(hass, "network", {"start": "DNS_1_LOW_WORD", "values": [1, 1]})
        assert response.status == 400
        assert "never read back" in response.body["error"]

    def test_the_ordinary_write_door_stays_sealed_on_the_block(self):
        # /network is not a loosening: the single-word /write keeps the
        # whole block forbidden forever (one lone word is a half-frame
        # waiting to happen).
        hass, coordinator = installed()
        for register in (SETTINGS, IP_LO, MASK_LO):
            response = post(hass, "write", {"register": register, "value": 1})
            assert response.status == 400
        assert coordinator.api.writes == []

"""Home Assistant tests for the BenQ Projector integration, against a fake projector."""

import asyncio

import benqprojector
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.benqprojector.const import DOMAIN

from .fake_projector import FakeProjector

MEDIA_PLAYER = "media_player.benq_lk935"
ASPECT = "select.benq_lk935_aspect_ratio"
LAMP = "sensor.benq_lk935_lamp_1_time"
BRIGHTNESS = "number.benq_lk935_brightness"
BRILLIANT = "switch.benq_lk935_brilliant_color"


@pytest.fixture(autouse=True)
def fast_reconnect(monkeypatch):
    """Shorten the reconnect back off of library versions that have one."""
    module = getattr(benqprojector, "benqprojector", benqprojector)
    monkeypatch.setattr(module, "_RECONNECT_DELAY_MIN", 0.2, raising=False)
    monkeypatch.setattr(module, "_RECONNECT_DELAY_MAX", 0.4, raising=False)


@pytest.fixture
async def fake():
    projector = FakeProjector()
    await projector.start()
    yield projector
    await projector.stop()


def make_entry(fake: FakeProjector) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="BenQ LK935",
        unique_id="c0:c4:f9:18:a6:2f",
        data={
            "host": "127.0.0.1",
            "port": fake.port,
            "model": "LK935",
            "type": "telnet",
        },
        options={"interval": 1},
    )


async def wait_state(hass: HomeAssistant, entity_id: str, expected, timeout=15.0):
    async with asyncio.timeout(timeout):
        while True:
            state = hass.states.get(entity_id)
            if state is not None and state.state == expected:
                return state
            await asyncio.sleep(0.1)


async def setup(hass: HomeAssistant, fake: FakeProjector) -> MockConfigEntry:
    entry = make_entry(fake)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_off_then_on(hass: HomeAssistant, fake: FakeProjector) -> None:
    entry = await setup(hass, fake)
    assert entry.state is ConfigEntryState.LOADED

    await wait_state(hass, MEDIA_PLAYER, STATE_OFF)
    # Lamp time is readable while off (upstream left it unavailable).
    await wait_state(hass, LAMP, "61")
    assert hass.states.get(ASPECT).state == STATE_UNAVAILABLE

    fake.power = "on"
    await wait_state(hass, MEDIA_PLAYER, STATE_ON)
    # "16:9" is shown as its option key (upstream showed unknown).
    await wait_state(hass, ASPECT, "16_9")
    await wait_state(hass, BRIGHTNESS, "50.0")
    await wait_state(hass, BRILLIANT, STATE_ON)

    state = hass.states.get(MEDIA_PLAYER)
    assert state.attributes["volume_level"] == 0.25
    # The generic config lists hdmi and hdmi2, so the first one is "hdmi1".
    assert state.attributes["source"] == "hdmi1"

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [d.identifiers for d in devices] == [{(DOMAIN, "c0:c4:f9:18:a6:2f")}]
    await unload(hass, entry)


async def test_setup_retries_when_projector_resets(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    fake.refuse = True
    entry = make_entry(fake)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_retries_when_model_unknown(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    """Upstream crashed with AssertionError and HA never retried."""
    fake.silent.add("modelname")
    entry = make_entry(fake)
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, "model": None})
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_recovers_after_connection_reset(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    entry = await setup(hass, fake)
    await wait_state(hass, MEDIA_PLAYER, STATE_OFF)

    fake.refuse = True
    fake.reset_connections()
    await wait_state(hass, MEDIA_PLAYER, STATE_UNAVAILABLE)

    fake.refuse = False
    fake.power = "on"
    await wait_state(hass, MEDIA_PLAYER, STATE_ON)
    await wait_state(hass, ASPECT, "16_9")
    await unload(hass, entry)


async def test_unload_while_disconnected_stops_polling(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    entry = await setup(hass, fake)
    await wait_state(hass, MEDIA_PLAYER, STATE_OFF)
    projector = entry.runtime_data.projector

    fake.refuse = True
    fake.reset_connections()
    await wait_state(hass, MEDIA_PLAYER, STATE_UNAVAILABLE)

    await unload(hass, entry)
    assert projector._read_task is None or projector._read_task.done()

    fake.refuse = False
    connections = fake.connections
    await asyncio.sleep(1.5)
    assert fake.connections == connections


async def test_turn_on_off_and_select(hass: HomeAssistant, fake: FakeProjector) -> None:
    entry = await setup(hass, fake)
    await wait_state(hass, MEDIA_PLAYER, STATE_OFF)
    # Skip the warm up, settings are only polled once the projector is fully on.
    entry.runtime_data.projector._poweron_time = 0

    await hass.services.async_call(
        "media_player", "turn_on", {"entity_id": MEDIA_PLAYER}, blocking=True
    )
    assert hass.states.get(MEDIA_PLAYER).state == STATE_ON
    assert fake.power == "on"
    await wait_state(hass, ASPECT, "16_9")

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": ASPECT, "option": "2_35"},
        blocking=True,
    )
    assert fake.values["asp"] == "2.35"
    await wait_state(hass, ASPECT, "2_35")

    await wait_state(hass, BRIGHTNESS, "50.0")
    await hass.services.async_call(
        "number", "set_value", {"entity_id": BRIGHTNESS, "value": 53}, blocking=True
    )
    assert fake.values["bri"] == "53"
    assert hass.states.get(BRIGHTNESS).state == "53.0"

    await hass.services.async_call(
        "media_player", "turn_off", {"entity_id": MEDIA_PLAYER}, blocking=True
    )
    assert fake.power == "off"
    await unload(hass, entry)


async def test_send_service_targets_device(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    entry = await setup(hass, fake)
    await wait_state(hass, MEDIA_PLAYER, STATE_OFF)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]

    response = await hass.services.async_call(
        DOMAIN,
        "send",
        {"device_id": device.id, "command": "ltim"},
        blocking=True,
        return_response=True,
    )
    assert response == {"response": "61"}
    await unload(hass, entry)


async def test_duplicate_device_is_merged(
    hass: HomeAssistant, fake: FakeProjector
) -> None:
    """Entities on the host:port device move to the MAC device, entity IDs unchanged."""
    entry = make_entry(fake)
    entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    stale = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"127.0.0.1:{fake.port}")},
        name="BenQ LK935",
    )
    enabled = entity_registry.async_get_or_create(
        "media_player",
        DOMAIN,
        f"{entry.entry_id}-projector",
        config_entry=entry,
        device_id=stale.id,
        suggested_object_id="deck_benq_lk935",
    )
    disabled = entity_registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{entry.entry_id}-qas",
        config_entry=entry,
        device_id=stale.id,
        suggested_object_id="deck_benq_lk935_quick_auto_search",
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await wait_state(hass, "media_player.deck_benq_lk935", STATE_OFF)

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert [d.identifiers for d in devices] == [{(DOMAIN, "c0:c4:f9:18:a6:2f")}]
    device = devices[0]
    assert device_registry.async_get(stale.id) is None
    assert entity_registry.async_get(enabled.entity_id).device_id == device.id
    moved = entity_registry.async_get(disabled.entity_id)
    assert moved is not None and moved.device_id == device.id
    await unload(hass, entry)

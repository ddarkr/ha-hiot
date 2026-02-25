# pyright: reportMissingImports=false

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.hiot.const import DOMAIN
from custom_components.hiot.coordinator import HiotEnergyCoordinator
from custom_components.hiot.sensor import HiotEnergySensor, async_setup_entry


async def test_sensor_setup_entry_creates_energy_entities(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotEnergyCoordinator(hass, mock_config_entry, mock_api_client)
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = {
        "energy_coordinator": coordinator,
    }

    add_entities = MagicMock()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    entities = add_entities.call_args[0][0]
    assert len(entities) == 9
    assert any(entity.unique_id == f"{mock_config_entry.entry_id}_energy_elec_usage" for entity in entities)
    assert any(entity.unique_id == f"{mock_config_entry.entry_id}_energy_water_fee" for entity in entities)
    assert any(entity.unique_id == f"{mock_config_entry.entry_id}_energy_gas_goal" for entity in entities)


async def test_energy_sensor_unit_conversion_and_attributes(
    hass, mock_config_entry, mock_api_client
) -> None:
    coordinator = HiotEnergyCoordinator(hass, mock_config_entry, mock_api_client)
    coordinator.data = {
        "ELEC": {
            "usage": {"usage": 64400, "sameAreaTypeUsage": 123000},
            "fee": {"fee": 7860},
            "goal": {"goal": 400000},
        },
        "WATER": {
            "usage": {"usage": 22800, "sameAreaTypeUsage": 20000},
            "fee": {"fee": 28500},
            "goal": {"goal": 200000},
        },
        "GAS": {
            "usage": {"usage": 72500, "sameAreaTypeUsage": 60000},
            "fee": {"fee": 0},
            "goal": {"goal": 200000},
        },
    }

    elec_usage = HiotEnergySensor(
        coordinator,
        mock_config_entry.entry_id,
        "ELEC",
        "usage",
    )
    elec_fee = HiotEnergySensor(
        coordinator,
        mock_config_entry.entry_id,
        "ELEC",
        "fee",
    )
    water_goal = HiotEnergySensor(
        coordinator,
        mock_config_entry.entry_id,
        "WATER",
        "goal",
    )
    gas_usage = HiotEnergySensor(
        coordinator,
        mock_config_entry.entry_id,
        "GAS",
        "usage",
    )

    assert elec_usage.native_value == 64.4
    assert elec_usage.extra_state_attributes == {"sameAreaTypeUsage": 123.0}
    assert elec_usage.native_unit_of_measurement == "kWh"
    assert elec_usage.icon == "mdi:flash"

    assert elec_fee.native_value == 7860
    assert elec_fee.native_unit_of_measurement == "KRW"

    assert water_goal.native_value == 200000
    assert water_goal.native_unit_of_measurement == "L"
    assert water_goal.icon == "mdi:target"

    assert gas_usage.native_value == 72.5
    assert gas_usage.extra_state_attributes == {"sameAreaTypeUsage": 60}
    assert gas_usage.native_unit_of_measurement == "m³"
    assert gas_usage.icon == "mdi:fire"

    assert elec_usage.device_info is not None
    assert elec_usage.device_info.get("identifiers") == {
        (DOMAIN, f"{mock_config_entry.entry_id}_energy")
    }

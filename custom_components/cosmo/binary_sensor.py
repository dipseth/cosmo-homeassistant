"""Binary sensors for each COSMO watch: emergency and powered-off."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .entity import CosmoEntity


@dataclass(frozen=True, kw_only=True)
class CosmoBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[CosmoBinaryDescription, ...] = (
    CosmoBinaryDescription(
        key="emergency",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda d: bool(d.get("emergencyMode")),
    ),
    CosmoBinaryDescription(
        key="powered_off",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: bool(d.get("shutdown")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: CosmoConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CosmoBinarySensor(coordinator, device_id, desc)
        for device_id in coordinator.data
        for desc in BINARY_SENSORS
    )


class CosmoBinarySensor(CosmoEntity, BinarySensorEntity):
    entity_description: CosmoBinaryDescription

    def __init__(self, coordinator, device_id: str, desc: CosmoBinaryDescription) -> None:
        super().__init__(coordinator, device_id, desc.key)
        self.entity_description = desc

    @property
    def is_on(self) -> bool | None:
        dev = self.device
        if not dev:
            return None
        return self.entity_description.value_fn(dev)

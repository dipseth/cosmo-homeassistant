"""Sensors for each COSMO watch: battery, last fix, status, and diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import CosmoConfigEntry
from .const import SOURCE_TYPES
from .entity import CosmoEntity


def _battery(dev: dict[str, Any]) -> int | None:
    v = dev.get("batteryLevel")
    return int(v) if isinstance(v, (int, float)) else None


def _ext_battery(dev: dict[str, Any]) -> int | None:
    v = dev.get("externalBatteryLevel")
    return int(v) if isinstance(v, (int, float)) else None


def _last_fix(dev: dict[str, Any]):
    return dt_util.parse_datetime(str(dev.get("gpsDate") or "")) or None


def _gps_source(dev: dict[str, Any]) -> str | None:
    return SOURCE_TYPES.get(dev.get("sourceType"), str(dev.get("sourceType") or "") or None)


@dataclass(frozen=True, kw_only=True)
class CosmoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[CosmoSensorDescription, ...] = (
    CosmoSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery,
    ),
    CosmoSensorDescription(
        key="external_battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
        value_fn=_ext_battery,
    ),
    CosmoSensorDescription(
        key="last_fix",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_fix,
    ),
    CosmoSensorDescription(
        key="gps_source",
        value_fn=_gps_source,
    ),
    CosmoSensorDescription(
        key="phone_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("gsmNumber"),
    ),
    CosmoSensorDescription(
        key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("firmwareVersion"),
    ),
    CosmoSensorDescription(
        key="imei",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.get("imei"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: CosmoConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CosmoSensor(coordinator, device_id, desc)
        for device_id in coordinator.data
        for desc in SENSORS
    )


class CosmoSensor(CosmoEntity, SensorEntity):
    """A single sensor value read from the map payload."""

    entity_description: CosmoSensorDescription

    def __init__(self, coordinator, device_id: str, desc: CosmoSensorDescription) -> None:
        super().__init__(coordinator, device_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        dev = self.device
        if not dev:
            return None
        return self.entity_description.value_fn(dev)

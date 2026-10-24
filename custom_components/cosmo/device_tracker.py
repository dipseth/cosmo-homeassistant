"""Device tracker: each COSMO watch's GPS position."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .const import SOURCE_TYPES
from .entity import CosmoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: CosmoConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CosmoDeviceTracker(coordinator, device_id) for device_id in coordinator.data
    )


class CosmoDeviceTracker(CosmoEntity, TrackerEntity):
    """GPS location of one watch."""

    _attr_translation_key = "location"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "location")

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        dev = self.device or {}
        return dev.get("latitude")

    @property
    def longitude(self) -> float | None:
        dev = self.device or {}
        return dev.get("longitude")

    @property
    def location_accuracy(self) -> int:
        dev = self.device or {}
        try:
            return int(dev.get("radius") or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def battery_level(self) -> int | None:
        dev = self.device or {}
        value = dev.get("batteryLevel")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        dev = self.device or {}
        return {
            "gps_source": SOURCE_TYPES.get(dev.get("sourceType"), dev.get("sourceType")),
            "last_fix": dev.get("gpsDate"),
            "valid": dev.get("isValid"),
            "phone_number": dev.get("gsmNumber"),
        }

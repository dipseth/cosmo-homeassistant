"""Base entity + device info for COSMO watches."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CosmoCoordinator


def device_name(device: dict[str, Any]) -> str:
    """Friendly name for a watch: the child's name, else the phone number, else id."""
    first = (device.get("firstName") or "").strip()
    last = (device.get("lastName") or "").strip()
    name = f"{first} {last}".strip()
    return name or device.get("gsmNumber") or f"COSMO {device.get('id')}"


def watch_device_info(device: dict[str, Any]) -> DeviceInfo:
    """One HA device per watch, keyed on the myFilip device id."""
    model = "JrTrack"
    hw = device.get("hardwareVersion") or ""
    if hw.startswith("JT5"):
        model = "JrTrack 5"
    elif hw.startswith("JT4"):
        model = "JrTrack 4"
    return DeviceInfo(
        identifiers={(DOMAIN, str(device.get("id")))},
        name=device_name(device),
        manufacturer=MANUFACTURER,
        model=model,
        sw_version=device.get("firmwareVersion"),
        serial_number=device.get("imei"),
        configuration_url="https://cosmotogether.com",
    )


class CosmoEntity(CoordinatorEntity[CosmoCoordinator]):
    """Entity backed by the map coordinator, scoped to one watch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CosmoCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = watch_device_info(coordinator.data[device_id])

    @property
    def device(self) -> dict[str, Any] | None:
        """Current data for this watch, if the account still lists it."""
        return (self.coordinator.data or {}).get(self.device_id)

    @property
    def available(self) -> bool:
        return super().available and self.device is not None

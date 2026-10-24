"""Buttons for each COSMO watch: locate now and ring (find my watch)."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CosmoConfigEntry
from .api import CosmoError
from .entity import CosmoEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: CosmoConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client
    entities: list[ButtonEntity] = []
    for device_id in coordinator.data:
        entities.append(CosmoLocateButton(coordinator, client, device_id))
        entities.append(CosmoRingButton(coordinator, client, device_id))
    async_add_entities(entities)


class _CosmoButton(CosmoEntity, ButtonEntity):
    def __init__(self, coordinator, client, device_id: str, key: str) -> None:
        super().__init__(coordinator, device_id, key)
        self._client = client


class CosmoLocateButton(_CosmoButton):
    """Ask the watch to report a fresh GPS fix, then refresh."""

    _attr_translation_key = "locate"

    def __init__(self, coordinator, client, device_id: str) -> None:
        super().__init__(coordinator, client, device_id, "locate")

    async def async_press(self) -> None:
        try:
            await self._client.async_refresh_location(int(self.device_id))
        except CosmoError as err:
            _LOGGER.warning("Locate request failed: %s", err)
            return
        await self.coordinator.async_request_refresh()


class CosmoRingButton(_CosmoButton):
    """Ring the watch (find my watch)."""

    _attr_translation_key = "ring"

    def __init__(self, coordinator, client, device_id: str) -> None:
        super().__init__(coordinator, client, device_id, "ring")

    async def async_press(self) -> None:
        try:
            await self._client.async_find_watch(int(self.device_id))
        except CosmoError as err:
            _LOGGER.warning("Ring request failed: %s", err)

"""Data coordinator for COSMO: one poll of v2/map keyed by device id."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CosmoAuthError, CosmoClient, CosmoError
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CosmoCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls GET v2/map and exposes {device_id(str): device dict}."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: CosmoClient
    ) -> None:
        interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} map",
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.client.async_map()
        except CosmoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CosmoError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[str, dict[str, Any]] = {}
        for dev in devices:
            dev_id = dev.get("id")
            if dev_id is None:
                continue
            result[str(dev_id)] = dev
        return result

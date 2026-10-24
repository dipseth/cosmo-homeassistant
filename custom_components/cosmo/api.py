"""Async client for the COSMO / myFilip cloud API.

COSMO: Mission Control is a white-label of the myFilip platform (whiteLabelId=18).

  Auth: POST v2/token          {whiteLabelId, email, password, appBuild} -> accessToken (+ refreshToken, expDate)
        POST v2/token/refresh  {refreshToken}                            -> fresh session
  Data: GET  v2/map            -> every watch with current location, battery, gpsDate, SafeZones
        POST v2/map/refresh    -> ask the watches to report a fresh fix
        POST v2/findMyWatch/{id} -> ring the watch

All data calls carry Authorization: Bearer <accessToken> plus the API version headers.
Reverse-engineered from com.cosmo.missioncontrol v3.4.1 (static analysis). Read-only by default.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .const import API_BASE, APP_BUILD, WHITE_LABEL_ID

_LOGGER = logging.getLogger(__name__)

USER_AGENT = "okhttp/4.9.0"
VERSION_HEADERS = {"Accept-Version": "v1.0", "X-Accept-Version": "1.0"}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
TOKEN_MARGIN = 120  # renew when fewer than this many seconds remain on expDate


class CosmoError(Exception):
    """Base error."""


class CosmoAuthError(CosmoError):
    """Credentials rejected (login failed, or Bearer refused)."""


class CosmoConnectionError(CosmoError):
    """Network / server problem."""


def _parse_exp(value: Any) -> float:
    """Parse the ISO-8601 expDate into a unix timestamp, 0 if unparseable."""
    if not value:
        return 0.0
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _unwrap(body: Any) -> dict[str, Any]:
    """Session responses wrap the token in `data`."""
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict):
            return data
        return body
    return {}


class CosmoClient:
    """Minimal client with proactive token renewal."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        refresh_token: str | None = None,
        on_token_update: Callable[[str | None], None] | None = None,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._refresh_token = refresh_token
        self._on_token_update = on_token_update
        self._token: str | None = None
        self._exp = 0.0
        self._lock = asyncio.Lock()

    @property
    def refresh_token(self) -> str | None:
        """Current refresh token (persist this across restarts)."""
        return self._refresh_token

    # ------------------------------------------------------------------ http
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        bearer: str | None = None,
    ) -> tuple[int, Any]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json", **VERSION_HEADERS}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        url = API_BASE + path.lstrip("/")
        try:
            async with self._session.request(
                method, url, json=json_body, headers=headers, timeout=REQUEST_TIMEOUT
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
                    body = {"_raw": (await resp.text())[:500]}
                return resp.status, body
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CosmoConnectionError(f"{method} {path}: {err}") from err

    # ------------------------------------------------------------------ auth
    def _store_session(self, data: dict[str, Any]) -> None:
        token = data.get("accessToken") or data.get("access_token")
        if not token:
            return
        self._token = token
        self._exp = _parse_exp(data.get("expDate"))
        new_refresh = data.get("refreshToken") or data.get("refresh_token")
        if new_refresh and new_refresh != self._refresh_token:
            self._refresh_token = new_refresh
            if self._on_token_update is not None:
                self._on_token_update(new_refresh)

    async def async_login(self) -> None:
        """Password login. Raises CosmoAuthError on bad credentials."""
        status, body = await self._request(
            "POST",
            "v2/token",
            json_body={
                "whiteLabelId": WHITE_LABEL_ID,
                "email": self._email,
                "password": self._password,
                "appBuild": APP_BUILD,
            },
        )
        data = _unwrap(body)
        if status == 200 and (data.get("accessToken") or data.get("access_token")):
            self._store_session(data)
            return
        message = body.get("message") if isinstance(body, dict) else body
        if status >= 500:
            raise CosmoConnectionError(f"login failed [{status}]: {message}")
        raise CosmoAuthError(f"login failed [{status}]: {message}")

    async def _async_try_refresh(self) -> bool:
        """Renew the session with the refresh token. False if the server refused."""
        if not self._refresh_token:
            return False
        status, body = await self._request(
            "POST", "v2/token/refresh", json_body={"refreshToken": self._refresh_token}
        )
        data = _unwrap(body)
        if status == 200 and (data.get("accessToken") or data.get("access_token")):
            self._store_session(data)
            return True
        if status >= 500:
            raise CosmoConnectionError(f"refresh failed [{status}]")
        _LOGGER.debug("Refresh token rejected [%s]; falling back to login", status)
        self._refresh_token = None
        return False

    async def async_ensure_token(self) -> str:
        """Return a Bearer token with at least TOKEN_MARGIN seconds left."""
        async with self._lock:
            if self._token and self._exp > time.time() + TOKEN_MARGIN:
                return self._token
            if await self._async_try_refresh():
                return self._token  # type: ignore[return-value]
            await self.async_login()
            return self._token  # type: ignore[return-value]

    def invalidate_token(self) -> None:
        """Forget the cached token so the next call re-authenticates."""
        self._token = None
        self._exp = 0.0

    # ------------------------------------------------------------------ data
    async def _authed(
        self, method: str, path: str, json_body: dict[str, Any] | None = None
    ) -> Any:
        """Authenticated request with one retry after a 401."""
        token = await self.async_ensure_token()
        status, body = await self._request(method, path, json_body=json_body, bearer=token)
        if status == 401:
            self.invalidate_token()
            token = await self.async_ensure_token()
            status, body = await self._request(method, path, json_body=json_body, bearer=token)
        if status == 401:
            raise CosmoAuthError(f"{method} {path}: unauthorized")
        if status >= 500:
            raise CosmoConnectionError(f"{method} {path}: HTTP {status}")
        if status not in (200, 201, 204):
            raise CosmoError(f"{method} {path}: HTTP {status}: {str(body)[:200]}")
        return body

    async def async_map(self) -> list[dict[str, Any]]:
        """GET v2/map -> list of watch dicts (location, battery, status, ...)."""
        body = await self._authed("GET", "v2/map")
        data = body.get("data") if isinstance(body, dict) else None
        devices = data.get("Devices") if isinstance(data, dict) else None
        return devices if isinstance(devices, list) else []

    async def async_safezones(self) -> list[dict[str, Any]]:
        """GET v2/safezones -> geofences on the account."""
        body = await self._authed("GET", "v2/safezones")
        data = body.get("data") if isinstance(body, dict) else body
        if isinstance(data, dict):
            data = data.get("SafeZones") or data.get("safezones") or data.get("items")
        return data if isinstance(data, list) else []

    async def async_refresh_location(self, device_id: int | None = None) -> None:
        """Ask the watch(es) to report a fresh fix (POST v2/map/refresh[/{id}])."""
        path = f"v2/map/refresh/{device_id}" if device_id is not None else "v2/map/refresh"
        await self._authed("POST", path)

    async def async_find_watch(self, device_id: int) -> None:
        """Ring the watch (POST v2/findMyWatch/{id})."""
        await self._authed("POST", f"v2/findMyWatch/{device_id}")

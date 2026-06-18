"""Async client for the Smart Pool Control owner portal.

The portal (owner.smartpoolcontrol.eu) is a Django web application with no
documented API. This client logs in with the owner's e-mail/password, keeps a
session cookie, scrapes the measurements page for status and submits the
existing Django forms / toggle endpoints to control the pool.

The client is intentionally self-contained (only depends on ``aiohttp``) so it
can be exercised outside Home Assistant as well.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html import unescape
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Regex helpers ------------------------------------------------------------

_CSRF_INPUT_RE = re.compile(
    r'name="csrfmiddlewaretoken"\s+value="([^"]+)"'
)
_REDIRECT_POOL_RE = re.compile(r"/pools/measurements/(\d+)/")
_POOL_HEADER_RE = re.compile(
    r"Pool:\s*(?P<name>.+?)\s*\((?P<mac>[0-9A-Fa-f:]{17})\)"
)


def _num(text: str | None) -> float | None:
    """Parse the first number in *text* (handles ``7.10``, ``692.0``...)."""
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", "."))
    return float(match.group(0)) if match else None


def _section(html: str, start: str, length: int = 800) -> str:
    """Return a slice of *html* starting at marker *start* (for scoping)."""
    idx = html.find(start)
    if idx == -1:
        return ""
    return html[idx : idx + length]


@dataclass
class PoolStatus:
    """Parsed snapshot of the measurements page."""

    online: bool = True
    name: str | None = None
    mac: str | None = None

    ph: float | None = None
    ph_target: float | None = None
    rx: float | None = None
    rx_target: float | None = None
    water_temperature: float | None = None
    water_temperature_target: float | None = None
    outside_temperature: float | None = None
    solar_temperature: float | None = None

    heating_on: bool | None = None
    cover_state: str | None = None  # "open" / "closed" / raw text
    pump_speed: str | None = None  # off/low/medium/high/maximum
    lighting_on: bool | None = None

    raw: dict[str, Any] = field(default_factory=dict)


class SmartPoolControlError(Exception):
    """Base error."""


class AuthenticationError(SmartPoolControlError):
    """Raised when login fails."""


class SmartPoolControlClient:
    """Talks to the Smart Pool Control owner portal."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        base_url: str,
        session: aiohttp.ClientSession | None = None,
        pool_id: str | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self._base_url = base_url.rstrip("/")
        self.pool_id = pool_id
        self._owns_session = session is None
        # A dedicated cookie jar is required to hold the Django session cookie.
        self._session = session or aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar()
        )

    # -- lifecycle ---------------------------------------------------------

    async def close(self) -> None:
        if self._owns_session:
            await self._session.close()

    async def __aenter__(self) -> SmartPoolControlClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # -- low level helpers -------------------------------------------------

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def _csrf_cookie(self) -> str | None:
        for cookie in self._session.cookie_jar:
            if cookie.key == "csrftoken":
                return cookie.value
        return None

    async def _get_text(self, path: str, **kwargs: Any) -> tuple[str, str]:
        """GET *path*; return (final_url, text)."""
        async with self._session.get(
            self._url(path), allow_redirects=True, **kwargs
        ) as resp:
            text = await resp.text()
            return str(resp.url), text

    # -- authentication ----------------------------------------------------

    async def async_login(self) -> None:
        """Authenticate against the portal and discover the pool id."""
        login_url = self._url("/login/")
        async with self._session.get(login_url) as resp:
            page = await resp.text()

        match = _CSRF_INPUT_RE.search(page)
        if not match:
            raise SmartPoolControlError("Could not find CSRF token on login page")
        token = match.group(1)

        data = {
            "csrfmiddlewaretoken": token,
            "username": self._username,
            "password": self._password,
        }
        # Django requires a matching Referer for HTTPS POSTs.
        async with self._session.post(
            login_url,
            data=data,
            headers={"Referer": login_url},
            allow_redirects=False,
        ) as resp:
            location = resp.headers.get("Location", "")
            if resp.status != 302 or location.rstrip("/").endswith("login"):
                raise AuthenticationError("Invalid e-mail or password")

        # The root URL redirects to /pools/measurements/<id>/ once logged in.
        if not self.pool_id:
            final_url, _ = await self._get_text("/")
            pid = _REDIRECT_POOL_RE.search(final_url)
            if pid:
                self.pool_id = pid.group(1)

        if not self.pool_id:
            raise SmartPoolControlError("Logged in but could not discover pool id")

    async def _ensure_session(self) -> None:
        """Re-login if the session cookie has expired."""
        for cookie in self._session.cookie_jar:
            if cookie.key == "sessionid":
                return
        await self.async_login()

    # -- reading -----------------------------------------------------------

    async def async_get_status(self) -> PoolStatus:
        """Fetch and parse the measurements page."""
        await self._ensure_session()
        path = f"/pools/measurements/{self.pool_id}/"
        final_url, html = await self._get_text(path)

        # Redirected back to login -> session died, retry once.
        if "/login" in final_url:
            await self.async_login()
            _, html = await self._get_text(path)

        return self._parse_status(html)

    @staticmethod
    def _parse_status(html: str) -> PoolStatus:
        status = PoolStatus()

        header = _POOL_HEADER_RE.search(html)
        if header:
            status.name = unescape(header.group("name")).strip()
            status.mac = header.group("mac").upper()

        # The portal injects a "POOL OFFLINE" script block only when offline.
        status.online = 'text("POOL OFFLINE")' not in html

        # pH ---------------------------------------------------------------
        ph_card = _section(html, 'id="card_PH"')
        m = re.search(r"/ph\"[^>]*>\s*([\d.]+)", ph_card)
        status.ph = _num(m.group(1)) if m else None
        m = re.search(r"Target:\s*([\d.]+)", ph_card)
        status.ph_target = _num(m.group(1)) if m else None

        # Rx / Redox -------------------------------------------------------
        rx_card = _section(html, 'id="card_RX"')
        m = re.search(r"/rx\"[^>]*>\s*([\d.]+)", rx_card)
        status.rx = _num(m.group(1)) if m else None
        m = re.search(r"Target:\s*([\d.]+)", rx_card)
        status.rx_target = _num(m.group(1)) if m else None

        # Temperatures -----------------------------------------------------
        water = _section(html, ">Water<")
        status.water_temperature = _temp_from(water)
        m = re.search(r"Target:\s*([\d.]+)", water)
        status.water_temperature_target = _num(m.group(1)) if m else None

        outside = _section(html, ">Buiten<")
        status.outside_temperature = _temp_from(outside)

        solar = _section(html, ">Solar<")
        status.solar_temperature = _temp_from(solar)

        # Heating ----------------------------------------------------------
        m = re.search(r"Heating\s+(on|off)", html, re.IGNORECASE)
        if m:
            status.heating_on = m.group(1).lower() == "on"

        # Cover / deck -----------------------------------------------------
        m = re.search(r"/deckcontrol\"[^>]*>([^<]+)</a>", html)
        if m:
            txt = unescape(m.group(1)).strip().lower()
            if "closed" in txt or "dicht" in txt:
                status.cover_state = "closed"
            elif "open" in txt:
                status.cover_state = "open"
            else:
                status.cover_state = txt

        # Pump speed -------------------------------------------------------
        m = re.search(r"/filtermenu\"[^>]*>([^<]+)</a>", html)
        if m:
            txt = unescape(m.group(1)).strip().lower()
            for speed in ("off", "low", "medium", "high", "maximum"):
                if speed in txt:
                    status.pump_speed = speed
                    break

        # Lighting ---------------------------------------------------------
        light = _section(html, 'id="lighting_status"', 400)
        if "fa-toggle-on" in light:
            status.lighting_on = True
        elif "fa-toggle-off" in light:
            status.lighting_on = False

        return status

    # -- writing -----------------------------------------------------------

    async def _toggle(self, path: str) -> None:
        await self._ensure_session()
        url = self._url(path)
        async with self._session.get(
            url, headers={"Referer": self._url(f"/pools/measurements/{self.pool_id}/")}
        ) as resp:
            if resp.status >= 400:
                raise SmartPoolControlError(f"Toggle {path} failed: HTTP {resp.status}")

    async def async_toggle_lighting(self) -> None:
        await self._toggle(f"/pools/lighting_toggle/{self.pool_id}/")

    async def async_cover_open(self) -> None:
        await self._toggle(f"/pools/settings/{self.pool_id}/deck_open")

    async def async_cover_close(self) -> None:
        await self._toggle(f"/pools/settings/{self.pool_id}/deck_close")

    async def async_cover_stop(self) -> None:
        await self._toggle(f"/pools/settings/{self.pool_id}/deck_stop")

    async def _post_settings(
        self,
        page: str,
        *,
        marker: str,
        overrides: dict[str, str] | None = None,
        remove: set[str] | None = None,
    ) -> None:
        """Submit a Django settings form, preserving existing field values.

        Fetches the settings page, scrapes the form identified by *marker*
        (the formset prefix, e.g. ``settings_ph``), applies *overrides*,
        removes any field names in *remove* (used to uncheck checkboxes) and
        POSTs everything back together with the management form.
        """
        await self._ensure_session()
        url = self._url(f"/pools/settings/{self.pool_id}/{page}")
        async with self._session.get(url) as resp:
            html = await resp.text()

        form_html = _extract_form(html, marker)
        if not form_html:
            raise SmartPoolControlError(f"Could not locate form on {page}")

        fields = _form_fields(form_html)
        for name in remove or set():
            fields.pop(name, None)
        fields.update(overrides or {})
        token = self._csrf_cookie()
        if token:
            fields["csrfmiddlewaretoken"] = token

        async with self._session.post(
            url,
            data=fields,
            headers={"Referer": url},
            allow_redirects=False,
        ) as resp:
            if resp.status >= 400:
                raise SmartPoolControlError(f"Saving {page} failed: HTTP {resp.status}")

    # Convenience setters --------------------------------------------------

    async def async_set_ph_target(self, value: float) -> None:
        await self._post_settings(
            "ph",
            marker="settings_ph",
            overrides={"settings_ph-0-ph_value_target": str(value)},
        )

    async def async_set_rx_target(self, value: float) -> None:
        await self._post_settings(
            "rx",
            marker="settings_rx",
            overrides={"settings_rx-0-rx_value_target": str(value)},
        )

    async def async_set_water_target(self, value: float) -> None:
        await self._post_settings(
            "temperaturegeneral",
            marker="settings_temperature",
            overrides={"settings_temperature-0-temperature_water_target": str(value)},
        )

    async def async_set_frost_protection(self, enabled: bool) -> None:
        field = "settings_temperature-0-temperature_frost_protection"
        if enabled:
            await self._post_settings(
                "temperaturegeneral",
                marker="settings_temperature",
                overrides={field: "on"},
            )
        else:
            await self._post_settings(
                "temperaturegeneral", marker="settings_temperature", remove={field}
            )

    async def async_set_pump_force(self, enabled: bool) -> None:
        field = "settings_filter-0-filter_pump_force_on"
        if enabled:
            await self._post_settings(
                "filtergeneral", marker="settings_filter", overrides={field: "on"}
            )
        else:
            await self._post_settings(
                "filtergeneral", marker="settings_filter", remove={field}
            )

    async def async_set_lighting_mode(self, mode: int) -> None:
        await self._post_settings(
            "lighting",
            marker="settings_lighting",
            overrides={"settings_lighting-0-lighting_configuration": str(mode)},
        )

    async def async_set_pump_speed(self, speed: int, schedule: int = 1) -> None:
        field = f"settings_filterschedule{schedule}-0-filterschedule{schedule}_pump_speed"
        await self._post_settings(
            f"filterschedule{schedule}",
            marker=f"settings_filterschedule{schedule}",
            overrides={field: str(speed)},
        )


# -- module level HTML helpers --------------------------------------------


def _temp_from(section: str) -> float | None:
    """Extract a temperature value from a measurement card section."""
    m = re.search(r"h5[^>]*>\s*([\d.]+)\s*(?:&deg;|\xb0)?C", section)
    if not m:
        # value may be wrapped differently; fall back to first number before C
        m = re.search(r"([\d.]+)\s*(?:&deg;|\xb0)?C", section)
    return _num(m.group(1)) if m else None


def _extract_form(html: str, contains_name: str) -> str | None:
    """Return the <form>...</form> block that contains *contains_name*."""
    for match in re.finditer(r"<form[^>]*>(.*?)</form>", html, re.DOTALL | re.IGNORECASE):
        block = match.group(0)
        if contains_name.split("-")[0] in block or contains_name in block:
            return block
    return None


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'{name}\s*=\s*"([^"]*)"', tag)
    return m.group(1) if m else None


def _form_fields(form_html: str) -> dict[str, str]:
    """Collect current name=value pairs from a form (Django convention).

    Checkboxes are only included when ``checked``. Selects use the selected
    option. The special override sentinel ``__keep__`` is stripped by the
    caller via dict.update afterwards.
    """
    fields: dict[str, str] = {}

    for tag in re.findall(r"<input[^>]*>", form_html, re.IGNORECASE):
        name = _attr(tag, "name")
        if not name or name == "csrfmiddlewaretoken":
            continue
        input_type = (_attr(tag, "type") or "text").lower()
        if input_type == "checkbox":
            if "checked" in tag.lower():
                fields[name] = "on"
            continue
        if input_type == "submit":
            continue
        fields[name] = unescape(_attr(tag, "value") or "")

    for sel in re.finditer(r"<select[^>]*>(.*?)</select>", form_html, re.DOTALL | re.IGNORECASE):
        name = _attr(sel.group(0), "name")
        if not name:
            continue
        opt = re.search(r'<option[^>]*value="([^"]*)"[^>]*selected', sel.group(1))
        if not opt:
            opt = re.search(r'<option[^>]*value="([^"]*)"', sel.group(1))
        fields[name] = opt.group(1) if opt else ""

    return fields

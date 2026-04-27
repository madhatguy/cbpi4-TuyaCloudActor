# -*- coding: utf-8 -*-
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cbpi.api import CBPiActor, CBPiExtension, ConfigType, Property, action, parameters

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TuyaCredentials:
    endpoint: str
    access_id: str
    access_secret: str
    username: str
    password: str
    country_code: str
    app_schema: str


class TuyaClient:
    """
    Thin wrapper around TuyaOpenAPI (sync) used from CBPi (async).
    We keep one connected client per credentials to avoid reconnecting on every toggle.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._cache: Dict[TuyaCredentials, Any] = {}

    async def _get_openapi(self, creds: TuyaCredentials):
        async with self._lock:
            openapi = self._cache.get(creds)
            if openapi is not None and getattr(openapi, "is_connect", lambda: True)():
                return openapi

            def _connect_sync():
                from tuya_iot import TuyaOpenAPI  # imported lazily for faster CBPi startup

                api = TuyaOpenAPI(creds.endpoint, creds.access_id, creds.access_secret)
                # Tuya SDK supports connect(username, password, country_code, schema)
                api.connect(creds.username, creds.password, creds.country_code, creds.app_schema)
                return api

            openapi = await asyncio.to_thread(_connect_sync)
            self._cache[creds] = openapi
            return openapi

    async def list_devices(self, creds: TuyaCredentials) -> List[Dict[str, Any]]:
        openapi = await self._get_openapi(creds)

        def _list_sync() -> List[Dict[str, Any]]:
            uid = getattr(getattr(openapi, "token_info", None), "uid", None)
            if not uid:
                raise RuntimeError("Tuya: missing uid after connect()")

            resp = openapi.get(f"/v1.0/users/{uid}/devices")
            if not isinstance(resp, dict) or not resp.get("success", False):
                raise RuntimeError(f"Tuya list devices failed: {resp}")
            return resp.get("result") or []

        return await asyncio.to_thread(_list_sync)

    async def device_functions(self, creds: TuyaCredentials, device_id: str) -> List[Dict[str, Any]]:
        openapi = await self._get_openapi(creds)

        def _func_sync() -> List[Dict[str, Any]]:
            # Try newer path first, then fallback (Tuya APIs differ by product line)
            for path in (
                f"/v1.0/iot-03/devices/{device_id}/functions",
                f"/v1.0/devices/{device_id}/functions",
            ):
                resp = openapi.get(path)
                if isinstance(resp, dict) and resp.get("success", False):
                    return resp.get("result") or []
            raise RuntimeError(f"Tuya get device functions failed: {resp}")

        return await asyncio.to_thread(_func_sync)

    async def set_switch(self, creds: TuyaCredentials, device_id: str, dp_code: str, value: bool) -> None:
        openapi = await self._get_openapi(creds)

        def _cmd_sync() -> None:
            body = {"commands": [{"code": dp_code, "value": value}]}
            last = None
            for path in (
                f"/v1.0/iot-03/devices/{device_id}/commands",
                f"/v1.0/devices/{device_id}/commands",
            ):
                last = openapi.post(path, body)
                if isinstance(last, dict) and last.get("success", False):
                    return
            raise RuntimeError(f"Tuya send command failed: {last}")

        await asyncio.to_thread(_cmd_sync)


_TUYA = TuyaClient()


def _get_creds_from_cbpi(cbpi) -> Optional[TuyaCredentials]:
    endpoint = cbpi.config.get("tuya_endpoint", None)
    access_id = cbpi.config.get("tuya_access_id", None)
    access_secret = cbpi.config.get("tuya_access_secret", None)
    username = cbpi.config.get("tuya_username", None)
    password = cbpi.config.get("tuya_password", None)
    country_code = cbpi.config.get("tuya_country_code", None)
    app_schema = cbpi.config.get("tuya_app_schema", None)

    if not all([endpoint, access_id, access_secret, username, password, country_code, app_schema]):
        return None

    return TuyaCredentials(
        endpoint=str(endpoint).strip(),
        access_id=str(access_id).strip(),
        access_secret=str(access_secret).strip(),
        username=str(username).strip(),
        password=str(password),
        country_code=str(country_code).strip(),
        app_schema=str(app_schema).strip(),
    )


class TuyaCloudConfig(CBPiExtension):
    def __init__(self, cbpi):
        self.cbpi = cbpi
        self._task = asyncio.create_task(self._ensure_settings())

    async def _ensure_settings(self):
        await self._ensure("tuya_endpoint", "", ConfigType.STRING, "Tuya Endpoint (e.g. https://openapi.tuyaeu.com)")
        await self._ensure("tuya_access_id", "", ConfigType.STRING, "Tuya Access ID / Client ID")
        await self._ensure("tuya_access_secret", "", ConfigType.STRING, "Tuya Access Secret / Client Secret")
        await self._ensure("tuya_username", "", ConfigType.STRING, "Tuya account username (email or phone)")
        await self._ensure("tuya_password", "", ConfigType.STRING, "Tuya account password")
        await self._ensure("tuya_country_code", "1", ConfigType.STRING, "Tuya account country code (e.g. 1, 44, 49, 972)")
        await self._ensure("tuya_app_schema", "smartlife", ConfigType.STRING, "Tuya app schema (smartlife or tuyaSmart)")

    async def _ensure(self, key: str, default: Any, typ: ConfigType, description: str):
        val = self.cbpi.config.get(key, None)
        if val is None:
            try:
                logger.info("Adding CBPi setting: %s", key)
                await self.cbpi.config.add(key, default, typ, description)
            except Exception:
                logger.warning("Unable to add CBPi setting %s (db busy?)", key)


@parameters(
    [
        Property.Text(label="Device ID", configurable=True, description="Tuya device id (use action 'List Tuya Devices')."),
        Property.Text(
            label="DP Code",
            configurable=True,
            description="Tuya datapoint code for ON/OFF (e.g. switch, switch_1, switch_led).",
        ),
    ]
)
class TuyaCloudActor(CBPiActor):
    def init(self):
        self.state = False
        self.device_id = str(self.props.get("Device ID", "")).strip()
        self.dp_code = str(self.props.get("DP Code", "switch")).strip() or "switch"

    @action(key="List Tuya Devices", parameters=[])
    async def list_devices(self, **kwargs):
        creds = _get_creds_from_cbpi(self.cbpi)
        if creds is None:
            logger.warning("Tuya credentials missing. Configure them in CBPi Settings.")
            return
        try:
            devices = await _TUYA.list_devices(creds)
            # Keep log readable: show name + id.
            compact = [{"name": d.get("name"), "id": d.get("id"), "category": d.get("category")} for d in devices]
            logger.info("Tuya devices (%s): %s", len(compact), compact)
            return compact
        except Exception as e:
            logger.exception("Failed to list Tuya devices: %s", e)

    @action(key="Show Tuya Device Functions", parameters=[])
    async def show_functions(self, **kwargs):
        cbpi = self.cbpi
        creds = _get_creds_from_cbpi(cbpi)
        if creds is None:
            logger.warning("Tuya credentials missing. Configure them in CBPi Settings.")
            return
        if not self.device_id:
            logger.warning("No Tuya device id configured for this actor.")
            return

        try:
            funcs = await _TUYA.device_functions(creds, self.device_id)
            logger.info("Tuya functions for %s: %s", self.device_id, funcs)
        except Exception as e:
            logger.exception("Failed to fetch Tuya functions: %s", e)

    async def on(self, power=0):
        creds = _get_creds_from_cbpi(self.cbpi)
        if creds is None:
            logger.warning("Tuya credentials missing. Configure them in CBPi Settings.")
            return
        if not self.device_id:
            logger.warning("No Tuya device id configured for this actor.")
            return

        try:
            await _TUYA.set_switch(creds, self.device_id, self.dp_code, True)
            self.state = True
        except Exception as e:
            logger.exception("Tuya ON failed: %s", e)

    async def off(self):
        creds = _get_creds_from_cbpi(self.cbpi)
        if creds is None:
            logger.warning("Tuya credentials missing. Configure them in CBPi Settings.")
            return
        if not self.device_id:
            logger.warning("No Tuya device id configured for this actor.")
            return

        try:
            await _TUYA.set_switch(creds, self.device_id, self.dp_code, False)
            self.state = False
        except Exception as e:
            logger.exception("Tuya OFF failed: %s", e)

    def get_state(self):
        return self.state

    async def run(self):
        # No background loop needed for basic ON/OFF control
        pass


def setup(cbpi):
    cbpi.plugin.register("Tuya Cloud Actor", TuyaCloudActor)
    cbpi.plugin.register("Tuya Cloud Config", TuyaCloudConfig)


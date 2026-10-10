"""Smoke test: import the integration against the installed Home Assistant.

Run by the Compatibility workflow. It installs the requirements of the ESPHome
core integration (this integration depends on it and uses the same client
library), imports every module, and makes the client API calls used by the integration
to check that they still accept the same arguments.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = REPO_ROOT / "custom_components" / "zonergy_venus"
MODULES = (
    "const",
    "cloud_api",
    "cloud",
    "manager",
    "entity",
    "sensor",
    "binary_sensor",
    "switch",
    "number",
    "config_flow",
)


def install_esphome_requirements() -> None:
    """Install what Home Assistant installs for its ESPHome integration."""
    import homeassistant
    from homeassistant.const import __version__ as ha_version

    manifest = (
        Path(homeassistant.__file__).parent / "components" / "esphome" / "manifest.json"
    )
    requirements = json.loads(manifest.read_text())["requirements"]
    print(
        f"::notice title=Tested against::Home Assistant {ha_version}, {', '.join(requirements)}"
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *requirements],
        check=True,
    )


def check_call(description: str, call: Callable[[], object]) -> None:
    """Fail when a client call no longer accepts the arguments we pass.

    The ESPHome client is compiled, so its signatures cannot be inspected.
    Calling it shows the same thing: a changed signature raises TypeError
    before anything else happens. Other errors (there is no device to talk
    to) are expected and ignored.
    """
    try:
        result = call()
    except TypeError as err:
        raise SystemExit(f"{description}: {err}") from err
    except Exception:  # noqa: BLE001
        return
    close = getattr(result, "close", None)
    if callable(close):
        close()


async def check_client_api() -> None:
    """Make the aioesphomeapi calls used by manager, config flow and entities."""
    from aioesphomeapi import APIClient, ReconnectLogic

    # Built exactly as async_setup_entry builds it.
    manager_module = importlib.import_module("custom_components.zonergy_venus.manager")
    manager = manager_module.ZonergyVenusManager(
        None,
        host="192.0.2.1",
        port=6053,
        password=None,
        encryption_key=None,
        connection_type="esphome",
    )
    assert manager.device_identifier == "192.0.2.1"
    client = manager.client

    async def on_connect() -> None: ...

    async def on_disconnect(expected_disconnect: bool) -> None: ...

    async def on_connect_error(err: Exception) -> None: ...

    check_call(
        "APIClient(...) in the config flow",
        lambda: APIClient(
            "192.0.2.1",
            6053,
            password=None,
            client_info="Zonergy Venus Home Assistant setup",
            noise_psk=None,
        ),
    )
    check_call(
        "ReconnectLogic(...)",
        lambda: ReconnectLogic(
            client=client,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            on_connect_error=on_connect_error,
            zeroconf_instance=None,
            name=None,
        ),
    )
    check_call("APIClient.connect(login=True)", lambda: client.connect(login=True))
    check_call(
        "APIClient.disconnect(force=True)", lambda: client.disconnect(force=True)
    )
    check_call(
        "APIClient.number_command(key, value, device_id=...)",
        lambda: client.number_command(1, 1.0, device_id=0),
    )
    check_call(
        "APIClient.switch_command(key, state, device_id=...)",
        lambda: client.switch_command(1, True, device_id=0),
    )
    for name in ("device_info_and_list_entities", "subscribe_states"):
        if not hasattr(APIClient, name):
            raise SystemExit(f"APIClient.{name} no longer exists")


def main() -> None:
    install_esphome_requirements()
    sys.path.insert(0, str(REPO_ROOT))

    package = importlib.import_module("custom_components.zonergy_venus")
    for name in MODULES:
        importlib.import_module(f"custom_components.zonergy_venus.{name}")
        print(f"imported {name}")

    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    const = importlib.import_module("custom_components.zonergy_venus.const")
    assert manifest["domain"] == const.DOMAIN
    assert callable(package.async_setup_entry)
    assert callable(package.async_unload_entry)

    asyncio.run(check_client_api())
    print("Smoke test passed")


def report_failure(error: BaseException) -> None:
    """Show the failure as an annotation on the workflow run page."""
    detail = "".join(traceback.format_exception(error)).strip()[-3000:]
    escaped = detail.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title=Smoke test failed::{escaped}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        report_failure(error)
        raise

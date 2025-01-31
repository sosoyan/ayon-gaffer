from typing import Any
from ayon_server.settings import BaseSettingsModel

DEFAULT_VALUES = {}


class GafferSettings(BaseSettingsModel):
    frontend_scopes: dict[str, Any] = {"settings": {}}

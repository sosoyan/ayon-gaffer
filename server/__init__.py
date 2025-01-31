from typing import Type

from ayon_server.addons import BaseServerAddon

from .settings import GafferSettings, DEFAULT_VALUES


class GafferAddon(BaseServerAddon):
    settings_model: Type[GafferSettings] = GafferSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)

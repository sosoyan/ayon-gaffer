import os
from ayon_core.addon import AYONAddon, IHostAddon

from .version import __version__


GAFFER_HOST_DIR = os.path.dirname(os.path.abspath(__file__))

class GafferAddon(AYONAddon, IHostAddon):
    """
    Gaffer addon class.
    """

    name = "gaffer"
    host_name = "gaffer"
    version = __version__

    def add_implementation_envs(self, env, _app):
        """
          Add requirements to GAFFER_EXTENSION_PATHS
        """
        gaf_ext_paths = "GAFFER_EXTENSION_PATHS"

        if gaf_ext_paths in env:
            env[gaf_ext_paths] += os.pathsep + GAFFER_HOST_DIR
        else:
            env[gaf_ext_paths] = GAFFER_HOST_DIR

    def get_launch_hook_paths(self, app):
        if app.host_name == self.host_name:
            return [os.path.join(GAFFER_HOST_DIR, "hooks")]

        return []

    def get_workfile_extensions(self):
        return [".gfr"]

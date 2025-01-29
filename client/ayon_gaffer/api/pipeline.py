import os

import pyblish.api
from ayon_core.lib import Logger
from ayon_core.pipeline import (register_creator_plugin_path,
                                register_loader_plugin_path)
from ayon_core.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

from ayon_gaffer import GAFFER_HOST_DIR


log = Logger.get_logger(__name__)

PLUGINS_DIR = os.path.join(GAFFER_HOST_DIR, "plugins")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")

class GafferHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    name = "gaffer"

    _context_plug = "ayon_context"

    def __init__(self, application):
        super(GafferHost, self).__init__()
        self.application = application

    def get_current_workfile(self):
        return ""

    def get_workfile_extensions(self):
        return [".gfr"]

    def open_workfile(self, filepath):
        return ""
    
    def save_workfile(self, filepath=None):
        print(filepath)
        return ""

    def install(self):
        pyblish.api.register_host("gaffer")
        
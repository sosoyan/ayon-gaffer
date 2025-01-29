import os

import pyblish.api
from ayon_core.lib import Logger
from ayon_core.pipeline import (register_creator_plugin_path,
                                register_loader_plugin_path)
from ayon_core.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

from ayon_gaffer import GAFFER_HOST_DIR
from ayon_gaffer.api.project import setup_project


log = Logger.get_logger(__name__)

PLUGINS_DIR = os.path.join(GAFFER_HOST_DIR, "plugins")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")

class GafferHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    """
    GafferHost class that integrates with the Gaffer application and provides
    functionalities for workfile management, loading, and publishing.
    Attributes:
    """
    name = "gaffer"

    _context_plug = "ayon_context"

    def __init__(self, application):
        super(GafferHost, self).__init__()
        self.application = application
        self.application.root()["scripts"].childAddedSignal().connect(setup_project, scoped = False)

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
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        
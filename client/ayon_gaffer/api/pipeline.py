import pyblish.api
from ayon_core.lib import Logger
from ayon_core.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost


log = Logger.get_logger(__name__)

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
    
    def save_workfile(self, dst_path=None):
        return ""

    def install(self):
        pyblish.api.register_host("gaffer")
        
import pyblish.api
from ayon_core.lib import Logger
from ayon_core.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost
from ayon_core.pipeline import get_current_task_name

from ayon_gaffer import GAFFER_HOST_DIR
from ayon_gaffer.api.signals import GafferSignal


log = Logger.get_logger("ayon_gaffer.api.pipeline")

def setup_project(_, script):
    GafferSignal.pre_task_changed()(script, get_current_task_name())
    GafferSignal.post_task_changed()(script, get_current_task_name())

    log.info("Task changed ...")

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
        
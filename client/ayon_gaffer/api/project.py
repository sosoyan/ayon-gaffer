from ayon_core.lib import Logger
from ayon_core.pipeline import get_current_task_name

from ayon_gaffer.api.signals import GafferSignal


log = Logger.get_logger("ayon_gaffer.api.project")

def setup_project(_, script):
    GafferSignal.pre_task_changed()(script, get_current_task_name())
    GafferSignal.post_task_changed()(script, get_current_task_name())

    log.info("Task changed ...")
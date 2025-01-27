from ayon_core.lib import Logger

from ayon_gaffer.api.signals import GafferSignal


log = Logger.get_logger("ayon_gaffer.api.project")

def setup_project(_, script, tasks=None):
    GafferSignal.pre_context_changed()(script, tasks)
    
    
    GafferSignal.post_context_changed()(script, tasks)
    log.info("Context has been updated ...")

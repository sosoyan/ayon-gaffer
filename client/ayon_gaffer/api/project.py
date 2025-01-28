from ayon_core.lib import Logger
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

from ayon_gaffer.api.signals import GafferSignal


log = Logger.get_logger("ayon_gaffer.api.project")

def setup_project(_, script):

    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    GafferSignal.pre_context_changed()(script)
    
    
    GafferSignal.post_context_changed()(script)
    log.info(f"Ayon context has been set to {project_name}{folder_path} | {task_name}")

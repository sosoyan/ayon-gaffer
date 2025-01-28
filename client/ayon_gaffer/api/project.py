import ayon_api
from ayon_core.lib import Logger
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

from ayon_gaffer.api.signals import GafferSignal

import GafferUI

log = Logger.get_logger("ayon_gaffer.api.project")

def setup_project(_, script_node):
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    GafferSignal.pre_context_changed()(script_node)
    
    task = ayon_api.get_task_by_folder_path(project_name,
                                            folder_path,
                                            task_name)
    
    task_atrib = task.get("attrib")

    if task_atrib is not None:
        script_node["frameRange"]["start"].setValue(task_atrib["frameStart"])
        script_node["frameRange"]["end"].setValue(task_atrib["frameEnd"])
        script_node["framesPerSecond"].setValue(task_atrib["fps"])
        script_node['defaultFormat']["displayWindow"]["min"]["x"].setValue(0)
        script_node['defaultFormat']["displayWindow"]["min"]["y"].setValue(0)
        script_node['defaultFormat']["displayWindow"]["max"]["x"].setValue(task_atrib["resolutionWidth"])
        script_node['defaultFormat']["displayWindow"]["max"]["y"].setValue(task_atrib["resolutionHeight"])
        script_node['defaultFormat']["pixelAspect"].setValue(task_atrib["pixelAspect"])

        playback = GafferUI.Playback.acquire(script_node.context())
        playback.setFrameRange(task_atrib["frameStart"], task_atrib["frameEnd"])

    
    GafferSignal.post_context_changed()(script_node)
    log.info(f"Ayon context has been set to {project_name}{folder_path} | {task_name}")

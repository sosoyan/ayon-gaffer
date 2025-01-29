import ayon_api
from ayon_core.lib import Logger
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

from ayon_gaffer.api.signals import GafferSignal

import imath
import Gaffer
import GafferUI


log = Logger.get_logger(__name__)

def set_script_variables(script_node, attrib):

    script_vars = script_node["variables"]
    exists_vars = [i["name"].getValue() for i in script_vars.children()]
        
    for attrib_name, attrib_value in sorted(attrib.items(), reverse=True):
        
        if isinstance(attrib_value, int):
            plug_type = Gaffer.IntPlug
            default_value = attrib_value
        
        elif isinstance(attrib_value, float):
            plug_type = Gaffer.FloatPlug
            default_value = attrib_value
        
        elif isinstance(attrib_value, str):
            plug_type = Gaffer.StringPlug
            default_value = attrib_value

        elif isinstance(attrib_value, (tuple, list)):
        
            if len(attrib_value) == 2:
                plug_type = Gaffer.V2iPlug
                default_value = imath.V2i(0, 0)
                attrib_value = imath.V2i(attrib_value[0], attrib_value[1])

        elif attrib_value is None:
            log.warning(f"{attrib_name} value is None skipping!")
            continue
        else:
            log.error(f"Unknown type of {type({attrib_value})} for {attrib_name} - {attrib_value} skipping!")
            continue

        if not attrib_name.startswith("ayon:"):
            attrib_name = f"ayon:{attrib_name}"
        
        if attrib_name not in exists_vars:
            script_vars.addChild(Gaffer.NameValuePlug(attrib_name,
                                                      plug_type(attrib_name,
                                                                 defaultValue=default_value,
                                                                 flags=Gaffer.Plug.Flags.Default | 
                                                                       Gaffer.Plug.Flags.Dynamic),
                                                      attrib_name))

        script_vars[attrib_name]["value"].setValue(attrib_value)

def setup_project(_, script_node):
    """ 
        Sets up global veraiables and projects settings
        for the current Ayon context - project/folder/task
    """
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    log.info(f"Ayon context has been set to {project_name}{folder_path} | {task_name}")

    GafferSignal.pre_context_changed()(script_node)
    
    task = ayon_api.get_task_by_folder_path(project_name,
                                            folder_path,
                                            task_name)
    
    task_atrib = task.get("attrib")

    if task_atrib is not None:

        task_atrib["projectName"] = project_name
        task_atrib["folderPath"] = folder_path
        task_atrib["taskName"] = task_name

        set_script_variables(script_node, task_atrib)

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


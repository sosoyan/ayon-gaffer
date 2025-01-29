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

def set_script_settings(script_node, attr):
        """
        Set various settings on a Gaffer script node based on provided attributes.
        Args:
            script_node (Gaffer.ScriptNode): The script node to configure.
            attr (dict): A dictionary containing the following keys:
        Returns:
            None
        """
        
        script_node["frameRange"]["start"].setValue(attr["frameStart"])
        script_node["frameRange"]["end"].setValue(attr["frameEnd"])
        script_node["framesPerSecond"].setValue(attr["fps"])
        script_node['defaultFormat']["displayWindow"]["min"]["x"].setValue(0)
        script_node['defaultFormat']["displayWindow"]["min"]["y"].setValue(0)
        script_node['defaultFormat']["displayWindow"]["max"]["x"].setValue(attr["resolutionWidth"])
        script_node['defaultFormat']["displayWindow"]["max"]["y"].setValue(attr["resolutionHeight"])
        script_node['defaultFormat']["pixelAspect"].setValue(attr["pixelAspect"])

        playback = GafferUI.Playback.acquire(script_node.context())
        playback.setFrameRange(attr["frameStart"], attr["frameEnd"])

def set_script_variables(script_node, attr):
    """
    Sets script variables on the given script node based on the provided attributes.
    Args:
        script_node (Gaffer.ScriptNode): The script node to set variables on.
        attr (dict): A dictionary of attribute names and their corresponding values. 
                     The values can be of type int, float, or str. Keys that do not 
                     start with "ayon:" will be prefixed with "ayon:".
    Notes:
        - If an attribute value is None, it will be skipped with a warning.
        - If an attribute name does not already exist in the script node's variables, 
          it will be added.
        - Existing attribute values will be updated with the provided values.
    """

    script_vars = script_node["variables"]
    exists_vars = [i["name"].getValue() for i in script_vars.children()]
        
    for attrib_name, attrib_value in sorted(attr.items(), reverse=True):
        
        if isinstance(attrib_value, int):
            plug_type = Gaffer.IntPlug
            default_value = attrib_value
        
        elif isinstance(attrib_value, float):
            plug_type = Gaffer.FloatPlug
            default_value = attrib_value
        
        elif isinstance(attrib_value, str):
            plug_type = Gaffer.StringPlug
            default_value = attrib_value

        elif attrib_value is None:
            log.warning(f"{attrib_name} value is None skipping!")
            continue
        else:
            log.error(f"Unknown type of 
                      {type({attrib_value})} for {attrib_name} - {attrib_value} skipping!")
            continue

        if not attrib_name.startswith("ayon:"):
            attrib_name = f"ayon:{attrib_name}"
        
        if attrib_name not in exists_vars:
            script_vars.addChild(
                Gaffer.NameValuePlug(
                    attrib_name,
                    plug_type(
                        attrib_name,
                        defaultValue=default_value,
                        flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic),
                    attrib_name))

        script_vars[attrib_name]["value"].setValue(attrib_value)    

def setup_project(_, script_node):
    """
    Sets up global veraiables and projects settings
    for the current Ayon context - project/folder/task
    
    Args:
        _ (Any): Unused argument.
        script_node (Gaffer.ScriptNode): The script node to configure.
    
    Returns:
        None
    """
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    script_node["variables"]["projectRootDirectory"]["value"].setValue(
        "${AYON_WORKDIR}/gaffer/projects/${project:name}")

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

        set_script_settings(script_node, task_atrib)
        set_script_variables(script_node, task_atrib)
        
    GafferSignal.post_context_changed()(script_node)


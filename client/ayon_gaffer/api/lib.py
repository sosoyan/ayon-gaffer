import ayon_api
from ayon_core.lib import Logger
from ayon_core.pipeline import context_tools
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

import Gaffer
import GafferUI


log = Logger.get_logger(__name__)

def retrieve_context():
    """
    Tries to retrieve the saved script context by setting project, folder,
    and task from the Gaffer script variables and updating the context.
    """
    script_vars = GafferScript.node["variables"]

    project_name = "ayon:projectName"
    folder_path = "ayon:folderPath"
    task_name = "ayon:taskName"

    if (project_name in script_vars.keys() and
        folder_path in script_vars.keys() and
        task_name in script_vars.keys()):

        project_name = script_vars[project_name]["value"].getValue()
        folder_path = script_vars[folder_path]["value"].getValue()
        task_name = script_vars[task_name]["value"].getValue()

        folder = ayon_api.get_folder_by_path(project_name,
                                             folder_path)
        task = ayon_api.get_task_by_folder_path(project_name,
                                                folder_path,
                                                task_name)

        if (folder is not None) and (task is not None):
            update_context(folder, task)
        else:
            log.warning(f"Could not retrive saved script context! "
                        f"{project_name}/{folder_path} | {task_name}")

def set_script_settings(script_node, attr):
    """
    Set various settings on a Gaffer script
    node based on provided attributes.
    """
    script_node["frameRange"]["start"].setValue(attr["frameStart"])
    script_node["frameRange"]["end"].setValue(attr["frameEnd"])
    script_node["framesPerSecond"].setValue(attr["fps"])

    display_window = script_node['defaultFormat']["displayWindow"]
    display_window["min"]["x"].setValue(0)
    display_window["min"]["y"].setValue(0)
    display_window["max"]["x"].setValue(attr["resolutionWidth"])
    display_window["max"]["y"].setValue(attr["resolutionHeight"])

    default_format = script_node['defaultFormat']
    default_format["pixelAspect"].setValue(attr["pixelAspect"])

    playback = GafferUI.Playback.acquire(script_node.context())
    playback.setFrameRange(attr["frameStart"], attr["frameEnd"])

def set_script_variables(script_node, attr):
    """
    Sets script variables on the given script
    node based on the provided attributes.
    """
    script_vars = script_node["variables"]
    exists_vars = [i["name"].getValue() for i in script_vars.children()]

    for attrib_name, attrib_value in sorted(attr.items(), reverse=True):

        if attrib_value is not None:

            if isinstance(attrib_value, int):
                plug_type = Gaffer.IntPlug
                default_value = attrib_value

            elif isinstance(attrib_value, float):
                plug_type = Gaffer.FloatPlug
                default_value = attrib_value

            elif isinstance(attrib_value, str):
                plug_type = Gaffer.StringPlug
                default_value = attrib_value
            else:
                log.error(f"Unknown type of {type({attrib_value})} \
                          for {attrib_name} - {attrib_value} skipping!")
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
                            flags=Gaffer.Plug.Flags.Default | \
                                  Gaffer.Plug.Flags.Dynamic),
                        attrib_name))

            script_vars[attrib_name]["value"].setValue(attrib_value)

def setup_project(script_container=None, script_node=None):
    """
    Sets up global veraiables and projects settings
    for the current Ayon context - project/folder/task
    """
    if (script_container is not None) and (script_node is not None):
        GafferScript.node = script_node
        GafferScript.container = script_container

        retrieve_context()

    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    GafferSignal.pre_context_changed()(GafferScript.node)

    GafferScript.node["variables"]["projectRootDirectory"]["value"].setValue(
        "${AYON_WORKDIR}")

    task = ayon_api.get_task_by_folder_path(project_name,
                                            folder_path,
                                            task_name)

    task_atrib = task.get("attrib")

    if task_atrib is not None:

        task_atrib["projectName"] = project_name
        task_atrib["folderPath"] = folder_path
        task_atrib["taskName"] = task_name

        set_script_settings(GafferScript.node, task_atrib)
        set_script_variables(GafferScript.node, task_atrib)

    GafferSignal.post_context_changed()(GafferScript.node)

def update_context(folder, task=None):
    """
    Update the current context based on the provided folder and task.

    If no task is provided, it attempts to find a task within the folder
    that matches the types "Lookdev" or "Lighting", otherwise picks the first
    task. If no such task is found, it logs a warning and returns.
    """
    project_name = get_current_project_name()

    if task is None:
        tasks = ayon_api.get_tasks_by_folder_path(project_name, folder["path"])

        if not tasks:
            log.warning(f"No tasks found for folder \
                '{folder['name']}', abort context change!")
            return

        task = next((t for t in tasks if t["taskType"]
                     in {"Lookdev", "Lighting"}), tasks[0])

    context_tools.change_current_context(folder, task)

    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    log.info(f"Ayon context has been set to "
             f"{project_name}{folder_path} | {task_name}")

    setup_project()

class GafferSignal(object):
    """
    A class to handle Gaffer signals for context changes.
    """
    __pre_context_changed = Gaffer.Signal1()
    __post_context_changed = Gaffer.Signal1()

    @classmethod
    def pre_context_changed(cls):
        """
        Method to access the pre-context changed signal.

        Returns:
            Signal: The pre-context changed signal.
        """
        return cls.__pre_context_changed

    @classmethod
    def post_context_changed(cls):
        """
        Method to access the post-context changed signal.

        Returns:
            Signal: The post-context changed signal.
        """
        return cls.__post_context_changed

class GafferScript(object):
    """
    GafferScript is a singleton class that manages a node and a container.
    """
    __node = None
    __container = None
    __instance = None

    @property
    def node(self):
        return self.__node

    @node.setter
    def node(self, value):
        self.__node = value

    @property
    def container(self):
        return self.__container

    @container.setter
    def container(self, value):
        self.__container = value

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

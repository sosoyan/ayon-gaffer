from functools import partial

import ayon_api

from ayon_core.lib import Logger
from ayon_core.tools.utils import host_tools
from ayon_core.pipeline import context_tools
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

import IECore
import GafferUI

from PySide2 import QtCore

from ayon_gaffer.api.lib import (GafferSignal, setup_project)


log = Logger.get_logger(__name__)

def init_ayon_menu(menu):
    """
    Initializes the Ayon menu with various options and commands.

    Args:
        menu: The menu object to which the Ayon menu items will be added.

    Returns:
        IECore.MenuDefinition: The constructed menu definition with all the Ayon menu items.
    """
    main_menu = IECore.MenuDefinition()
    
    main_menu.append("Create...", {"command": lambda: host_tools.show_publisher(tab="create")})
    main_menu.append("Load...", {"command": lambda: host_tools.show_loader(use_context=True)})
    main_menu.append("Publish...", {"command": lambda: host_tools.show_publisher(tab="publish")})
    main_menu.append("Manage...", {"command": host_tools.show_scene_inventory})
    main_menu.append("Library...", {"command": host_tools.show_library_loader})
    main_menu.append("WorkFilesDivider", {"divider": True})
    main_menu.append("Work Files...", {"command": host_tools.show_workfiles})

    return main_menu

def update_context_menu_text(script_node):
    """
    Updates the text of the context menu in the Gaffer UI with the current project name,
    folder path, and task name.
    Args:
        script_node (Gaffer.ScriptNode): The script node for which the context menu text
                                         needs to be updated.
    The function retrieves the current project name, folder path, and task name, and then
    updates the context menu text in the Gaffer UI. If the script window is not visible,
    it sets a timer to retry after 1 second. The function assumes that the context menu
    item to be updated is labeled "AYON".
    """
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    script_window = GafferUI.ScriptWindow.acquire(script_node)

    if not script_window.visible():
        QtCore.QTimer.singleShot(1000, partial(update_context_menu_text, script_node))
        return

    container = script_window.getChild()
    menu_bar = container[0]
    if not isinstance(menu_bar, GafferUI.MenuBar):
        menu_bar = menu_bar[0]

    action_list = menu_bar._qtWidget().actions()

    for idx, action in enumerate(action_list):
        if action.text() == "AYON":
            context_menu = action_list[idx+1]
            context_menu.setText(f"{project_name}{folder_path} | {task_name}")
    
def update_context(root, folder, task=None):
    """
    Update the current context based on the provided folder and task.
    This function updates the context by setting the current folder and task.
    If no task is provided, it attempts to find tasks associated with the folder
    and sets the context to either a "Lookdev" or "Lighting" task if available,
    otherwise it sets the context to the first available task. If no tasks are found,
    it logs a warning and aborts the context change.
    Args:
        root (dict): The root dictionary containing script information.
        folder (dict): The folder dictionary containing folder details.
        task (dict, optional): The task dictionary containing task details. Defaults to None.
    Returns:
        None
    """
    project_name = get_current_project_name()

    folder = ayon_api.get_folder_by_id(project_name, folder["id"])
    
    if task is None:
        tasks = ayon_api.get_tasks_by_folder_path(project_name, folder["path"])

        if tasks:
            for task in tasks:
                if task["taskType"] == "Lookdev":
                    context_tools.change_current_context(folder, task)
                    break
                elif task["taskType"] == "Lighting":
                    context_tools.change_current_context(folder, task)
                    break
            else:
                context_tools.change_current_context(folder, tasks[0])
        else:
            log.warning(f"No tasks found for folder '{folder['name']}', abort context change!")
            return
    else:
        context_tools.change_current_context(folder, task)

    setup_project()

def init_context_menu_items(root, context_menu, folder):
    """
    Initializes context menu items recursively based on the folder structure.
    Args:
        root (object): The root object that will be passed to the update_context function.
        context_menu (IECore.MenuDefinition): The context menu to which items will be added.
        folder (dict): A dictionary representing the folder structure. It should contain
                       a "name" key for the folder name and optionally a "children" key
                       which is a list of child folders.
    Returns:
        None
    """

    if folder.get("children"):
        
        folder_menu = IECore.MenuDefinition()
        context_menu.append(folder["name"], {"subMenu": folder_menu})

        for child_folder in folder["children"]:
            
            child_folder_menu = IECore.MenuDefinition()  
            folder_menu.append(child_folder["name"], {"subMenu": child_folder_menu})
            
            init_context_menu_items(root, folder_menu, child_folder)
    else:
        context_menu.append(folder["name"], {"command": partial(update_context, root, folder)})

def init_context_menu(root):
    """
    Initializes the context menu for the given root element.
    This function creates a context menu based on the current project and folder path.
    It populates the menu with items representing the folder hierarchy and tasks available
    in the current folder. The context menu includes a divider and a submenu for setting tasks.
    Args:
        root: The root element to which the context menu will be attached.
    Returns:
        IECore.MenuDefinition: The constructed context menu.
    """
    
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()

    context_menu = IECore.MenuDefinition()
    set_tasks_menu = IECore.MenuDefinition()

    hierarchy = ayon_api.get_folders_hierarchy(project_name)["hierarchy"]
    
    for folder in hierarchy:
        init_context_menu_items(root, context_menu, folder)
    
    context_menu.append("contextDivider", {"divider": True})
    context_menu.append("Set Task", {"subMenu": set_tasks_menu})
    
    tasks = ayon_api.get_tasks_by_folder_path(project_name, folder_path)

    current_folder = ayon_api.get_folder_by_path(project_name, folder_path)

    for task in tasks:
        set_tasks_menu.append(task['name'], {"command": partial(update_context, root, current_folder, task)})

    return context_menu

def install_menu(application):
    """
    Installs custom menus into the Gaffer application.

    This function adds two custom menus, "AYON" and "Context", to the top menu of the Gaffer application.
    It also connects a signal to update the context menu text when the context changes.

    Args:
        application (Gaffer.Application): The Gaffer application instance.

    Returns:
        None
    """
    root = application.root()
    top_menu = GafferUI.ScriptWindow.menuDefinition(root)
    top_menu.append("AYON", {"subMenu": init_ayon_menu})
    top_menu.append("Context", {"subMenu": partial(init_context_menu, root)})

    GafferSignal.post_context_changed().connect(update_context_menu_text, scoped = False)

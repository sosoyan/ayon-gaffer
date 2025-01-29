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

from ayon_gaffer.api.project import setup_project
from ayon_gaffer.api.signals import GafferSignal


log = Logger.get_logger(__name__)

def get_main_window(menu):
    script_window = menu.ancestor(GafferUI.ScriptWindow)
    return script_window._qtWidget()  

def init_ayon_menu(menu):
    main_menu = IECore.MenuDefinition()

    main_menu.append(
        f"Create...",
        {"command": lambda menu: host_tools.show_publisher(
            parent=get_main_window(menu),
            tab="create")}
        )
    main_menu.append(
        f"Load...",
        {"command": lambda menu: host_tools.show_loader(
            parent=get_main_window(menu),
            use_context=True)}
    )
    main_menu.append(
        f"Publish...",
        {"command": lambda menu: host_tools.show_publisher(
            parent=get_main_window(menu),
            tab="publish")}
    )
    main_menu.append(
        f"Manage...",
        {"command": lambda menu: host_tools.show_scene_inventory(
            parent=get_main_window(menu))}
    )
    main_menu.append(
        f"Library...",
        {"command": lambda menu: host_tools.show_library_loader(
            parent=get_main_window(menu))}
    )

    main_menu.append(f"ActionsDivider", {"divider": True})
    main_menu.append(
        f"Set frame range...",
        {"command": lambda menu: set_frame_range_callback(menu)}
    )
    main_menu.append(
        f"Update context variables",
        {"command": lambda menu: update_root_context_variables_callback(menu)}
    )

    main_menu.append(f"WorkFilesDivider", {"divider": True})
    main_menu.append(
        f"Work Files...",
        {"command": lambda menu: host_tools.show_workfiles(
            parent=get_main_window(menu))}
    )

    return main_menu

def update_context_menu_text(script_node):

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
    menu_text = f"{project_name}{folder_path} | {task_name}"

    action_list[-1].setText(menu_text)
    
def update_context(root, folder, task=None):
    project_name = get_current_project_name()

    folder = ayon_api.get_folder_by_id(project_name, folder["id"])
    
    if task is None:
        tasks = ayon_api.get_tasks_by_folder_path(project_name, folder["path"])

        if tasks:
            # Try to set Lookdev or Lighting task, otherwise set the first existing
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

    setup_project(root["scripts"], 
                  root["scripts"]["ScriptNode"])

def init_context_menu_items(root, context_menu, folder):
    
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
    root = application.root()
    top_menu = GafferUI.ScriptWindow.menuDefinition(root)
    top_menu.append("AYON", {"subMenu": init_ayon_menu})
    top_menu.append("Context", {"subMenu": partial(init_context_menu, root)})

    GafferSignal.post_context_changed().connect(update_context_menu_text, scoped = False)

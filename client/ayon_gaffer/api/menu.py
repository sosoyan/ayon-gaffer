import ayon_api
from ayon_core.tools.utils import host_tools
from ayon_core.pipeline import context_tools
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

import IECore
import Gaffer
import GafferUI

from PySide2 import QtCore

from ayon_gaffer.api.project import setup_project
from ayon_gaffer.api.signals import GafferSignal


__context_menu = IECore.MenuDefinition()
__set_tasks_menu = IECore.MenuDefinition()

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

def update_context_menu_text(script, tasks):
    script_window = GafferUI.ScriptWindow.acquire(script)

    if not script_window.visible():
        QtCore.QTimer.singleShot(1000, lambda: update_context_menu_text(script, tasks))
        return
    
    container = script_window.getChild()
    menu_bar = container[0]
    if not isinstance(menu_bar, GafferUI.MenuBar):
        menu_bar = menu_bar[0]

    action_list = menu_bar._qtWidget().actions()
    menu_text = f"{get_current_project_name()}{get_current_folder_path()} | {get_current_task_name()}"

    action_list[-1].setText(menu_text)
    
    #for task in tasks:
    #    __set_tasks_menu.append(task["name"], {"command": lambda: context_tools.change_current_context(None, task)})
    
def update_context(root, item):
    project = get_current_project_name()

    folder = ayon_api.get_folder_by_id(project, item["id"])
    tasks = ayon_api.get_tasks_by_folder_path(project, folder["path"])
    
    for task in tasks:
        if task["taskType"] == "Lookdev":
            context_tools.change_current_context(folder, task)
            break
        elif task["taskType"] == "Lighting":
            context_tools.change_current_context(folder, task)
            break
    else:
        context_tools.change_current_context(folder, tasks[0])
    
    setup_project(root["scripts"], 
                  root["scripts"]["ScriptNode"],
                  tasks)

def init_context_menu_items(root, menu, item):
    
    if item.get('children'):
        
        item_menu = IECore.MenuDefinition()
        menu.append(item['name'], {"subMenu": item_menu})

        for child in item['children']:
            
            child_menu = IECore.MenuDefinition()  
            item_menu.append(child['name'], {"subMenu": child_menu})
            
            init_context_menu_items(root, item_menu, child)
    else:
        menu.append(item['name'], {"command": lambda: update_context(root, item)})

def init_context_menu(root, menu):
    
    hierarchy = ayon_api.get_folders_hierarchy(get_current_project_name())["hierarchy"]
    
    for item in hierarchy:
        init_context_menu_items(root, __context_menu, item)
    
    __context_menu.append("Set Task", {"subMenu": __set_tasks_menu})

    return __context_menu

def install_menu(application):
    root = application.root()
    top_menu = GafferUI.ScriptWindow.menuDefinition(root)
    top_menu.append("AYON", {"subMenu": init_ayon_menu})
    top_menu.append("Context", {"subMenu": lambda: init_context_menu(root, top_menu)})

    GafferSignal.post_context_changed().connect(update_context_menu_text, scoped = False)

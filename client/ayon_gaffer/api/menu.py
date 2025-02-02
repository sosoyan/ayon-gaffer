from functools import partial

import ayon_api

from ayon_core.lib import Logger
from ayon_core.tools.utils import host_tools
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

import IECore
import GafferUI

from PySide2 import QtCore

from ayon_gaffer.api.lib import (GafferSignal, update_context)


log = Logger.get_logger(__name__)

def init_ayon_menu(menu):
    """
    Initializes the Ayon menu with various options and commands.
    """
    main_menu = IECore.MenuDefinition()

    main_menu.append(
        "Create...", {"command":
                      lambda: host_tools.show_publisher(tab="create")})
    main_menu.append(
        "Load...", {"command":
                    lambda: host_tools.show_loader(use_context=True)})
    main_menu.append(
        "Publish...", {
            "command": lambda: host_tools.show_publisher(tab="publish")})
    main_menu.append(
        "Manage...", {"command":
                      host_tools.show_scene_inventory})
    main_menu.append(
        "Library...", {
            "command": host_tools.show_library_loader})
    main_menu.append(
        "WorkFilesDivider", {"divider": True})
    main_menu.append(
        "Work Files...", {
            "command": host_tools.show_workfiles})

    return main_menu

def update_context_menu_text(script_node):
    """
    Updates the text of a context menu in the Gaffer UI with the current
    project, folder, and task names.
    """
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    script_window = GafferUI.ScriptWindow.acquire(script_node)

    if not script_window.visible():
        QtCore.QTimer.singleShot(
            1000, partial(update_context_menu_text, script_node))
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

def init_context_menu_items(context_menu, item):
    """
    Initializes context menu items recursively based on the folder structure.
    """
    if item.get("children"):

        item_menu = IECore.MenuDefinition()
        context_menu.append(item["name"], {"subMenu": item_menu})

        for child_item in item["children"]:

            child_item_menu = IECore.MenuDefinition()
            item_menu.append(
                child_item["name"], {"subMenu": child_item_menu})

            init_context_menu_items(item_menu, child_item)
    else:
        project_name = get_current_project_name()
        folder = ayon_api.get_folder_by_id(project_name, item["id"])
        context_menu.append(
            folder["name"], {"command": partial(update_context, folder)})

def init_context_menu(menu):
    """
    Initializes the context menu for the given root element.
    """
    project_name = get_current_project_name()
    folder_path = get_current_folder_path()

    # Create Context menu
    context_menu = IECore.MenuDefinition()

    hierarchy = ayon_api.get_folders_hierarchy(project_name)["hierarchy"]

    for item in hierarchy:
        init_context_menu_items(context_menu, item)

    # Create Set Task sub menu
    set_tasks_menu = IECore.MenuDefinition()
    context_menu.append("contextDivider", {"divider": True})
    context_menu.append("Set Task", {"subMenu": set_tasks_menu})

    tasks = ayon_api.get_tasks_by_folder_path(project_name, folder_path)

    current_folder = ayon_api.get_folder_by_path(project_name, folder_path)

    for task in tasks:
        set_tasks_menu.append(
            task['name'], {"command":
                           partial(update_context, current_folder, task)})

    return context_menu

def install_menu(application):
    """
    Installs custom menus into the Gaffer application.
    """
    root = application.root()
    top_menu = GafferUI.ScriptWindow.menuDefinition(root)
    top_menu.append("AYON", {"subMenu": init_ayon_menu})
    top_menu.append("Context", {"subMenu": init_context_menu})

    GafferSignal.post_context_changed().connect(
        update_context_menu_text, scoped = False)

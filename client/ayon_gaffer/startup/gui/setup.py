import sys
from ayon_core.tools.utils import host_tools
from ayon_core.pipeline import (get_current_folder_path,
                                get_current_task_name)

from PySide2 import QtCore

import IECore
import Gaffer
import GafferUI

__pre_task_changed_signal = Gaffer.Signal2()
__post_task_changed_signal = Gaffer.Signal2()

self = sys.modules[__name__]
self.root = None

def set_root(root: Gaffer.ScriptNode):
    self.root = root

def get_main_window(menu):
    script_window = menu.ancestor(GafferUI.ScriptWindow)
    print(script_window)
    print(dir(script_window))
    set_root(script_window.scriptNode())
    return script_window._qtWidget()

def _init_ayon_menu(menu):
    
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

def _init_context_menu(menu):
    context_menu = IECore.MenuDefinition()
    
    context_menu.append(
        f"Switch...",
        {"command": lambda menu: host_tools.show_publisher(
            parent=get_main_window(menu),
            tab="create")}
        )
    return context_menu

def _install_menus(script):
    top_menu = GafferUI.ScriptWindow.menuDefinition(application)
    top_menu.append("AYON", {"subMenu": _init_ayon_menu})
    top_menu.append("Context", {"subMenu": _init_context_menu})

    __post_task_changed_signal.connect(update_shot_menu, scoped = False)

def setup_project(_, script):
    __pre_task_changed_signal(script, get_current_task_name())
    print("setup_project")
    __post_task_changed_signal(script, get_current_task_name())

def update_shot_menu(script, task):
    script_window = GafferUI.ScriptWindow.acquire(script)

    if not script_window.visible():
        QtCore.QTimer.singleShot(1000, lambda: update_shot_menu(script, task))
        return
    
    container = script_window.getChild()
    menu_bar = container[0]
    if not isinstance(menu_bar, GafferUI.MenuBar):
        menu_bar = menu_bar[0]

    action_list = menu_bar._qtWidget().actions()
    menu_text = "{} | {}".format(get_current_folder_path(), task) 
    action_list[-1].setText(menu_text)

application.root()["scripts"].childAddedSignal().connect(setup_project, scoped = False)

_install_menus(application)

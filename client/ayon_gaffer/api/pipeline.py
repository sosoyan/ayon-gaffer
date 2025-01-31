import os
import json

import pyblish.api
from ayon_core.lib import Logger
from ayon_core.pipeline import (register_creator_plugin_path,
                                register_loader_plugin_path,
                                register_workfile_build_plugin_path)
from ayon_core.host import HostBase, IWorkfileHost, ILoadHost, IPublishHost

from ayon_gaffer import GAFFER_HOST_DIR
from ayon_gaffer.api.lib import (GafferScript, setup_project)

import Gaffer
import GafferUI.FileMenu

log = Logger.get_logger(__name__)

PLUGINS_DIR = os.path.join(GAFFER_HOST_DIR, "plugins")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
WORKFILE_BUILD_PATH = os.path.join(PLUGINS_DIR, "workfile_build")

# A prefix used for storing JSON blobs in string plugs
JSON_PREFIX = "JSON:::"

class GafferHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    """
    GafferHost class that integrates with the Gaffer application and provides
    functionalities for workfile management, loading, and publishing.
    """

    name = "gaffer"
    ayon_context = "ayon_context"

    def __init__(self, application):
        super(GafferHost, self).__init__()
        self.application = application
        self.application.root()["scripts"].childAddedSignal().connect(setup_project, scoped = False)

    def install(self):
        pyblish.api.register_host("gaffer")
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        
        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

    def close_window(self, script_window):
        script_window.close()

    def has_unsaved_changes(self):
        return GafferScript.node["unsavedChanges"].getValue()

    def get_current_workfile(self):
        return GafferScript.node["fileName"].getValue()

    def substitute(self, value):
        return GafferScript.node.context().substitute(value)

    def get_workfile_extensions(self):
        return [".gfr"]

    def open_workfile(self, filepath):
        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))
        
        script_window = GafferUI.ScriptWindow.acquire(GafferScript.node)

        GafferUI.FileMenu.addScript(self.application.root(), filepath)
        GafferUI.EventLoop.addIdleCallback(lambda: self.close_window(script_window))

    def save_workfile(self, dst_path=None):

        if not dst_path:
            dst_path = self.get_current_workfile()

        dst_path = dst_path.replace("\\", "/")

        GafferScript.node.serialiseToFile(dst_path)
        GafferScript.node["fileName"].setValue(dst_path)
        GafferScript.node["unsavedChanges"].setValue(False)

        GafferUI.FileMenu.addRecentFile(self.application, dst_path)
        
        setup_project()
    
    def update_context_data(self, data, changes):
        data_str = json.dumps(data)
        self.user_plug = GafferScript.node["user"]
        self.user_plug[self.ayon_context] = Gaffer.StringPlug(
            defaultValue=data_str,
            flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
        )

    def get_context_data(self):
        self.user_plug = GafferScript.node["user"]
        if self.ayon_context in self.user_plug:
            data_str = self.user_plug[self.ayon_context].getValue()
            return json.loads(data_str)
        return {}
    
    def work_root(self, session):
        proj_root_dir_value =  GafferScript.node["variables"]["projectRootDirectory"]["value"].getValue()
        script_dir_path = os.path.join(self.substitute(proj_root_dir_value), "scripts").replace("\\", "/")

        print(script_dir_path)
        return script_dir_path
        
def imprint_container(node: Gaffer.Node,
                      name: str,
                      namespace: str,
                      context: dict,
                      loader: str = None):
    """Imprint a Loader with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        node (Gaffer.Node): The node in Gaffer to imprint as container,
            usually a node loaded by a Loader.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.

    Returns:
        None

    """
    data = {
        "schema": "openpype:container-2.0",
        "id": AYON_CONTAINER_ID,
        "name": str(name),
        "namespace": str(namespace),
        "loader": str(loader),
        "representation": str(context["representation"]["id"]),
    }
    imprint(node, data)


def imprint(node: Gaffer.Node,
            data: dict,
            section: str = "Ayon"):
    """Store and persist data on a node as `user` data.

    Args:
        node (Gaffer.Node): The node to store the data on.
            This can also be the workfile's root script node.
        data (dict): The key, values to store.
            Any `dict` values will be treated as JSON data and stored as
            string with `JSON:::` as a prefix to the value.
        section (str): Used to register the plug into a subsection in
            the user data allowing them to group data together.

    Returns:

    """

    FLAGS = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic

    for key, value in data.items():
        # Dict to JSON
        if isinstance(value, dict):
            value = json.dumps(value)
            value = f"{JSON_PREFIX}{value}"

        if key in node["user"]:
            # Set existing attribute
            try:
                if value is None:
                    value = ""
                print(value)
                node["user"][key].setValue(value)
                continue
            except Exception:
                # If an exception occurs then we'll just replace the key
                # with a new plug (likely types have changed)
                log.warning("Unable to set %s attribute %s to value %s (%s). "
                            "Likely there is a value type mismatch. "
                            "Plug will be replaced.",
                            node.getName(), key, value, type(value),
                            exc_info=sys.exc_info())
                pass

        if value is None:
            value = "<None>"

        # Generate new plug with value as default value
        if isinstance(value, str):
            plug = Gaffer.StringPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, bool):
            plug = Gaffer.BoolPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, float):
            plug = Gaffer.FloatPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, int):
            plug = Gaffer.IntPlug(key, defaultValue=value, flags=FLAGS)
        else:
            raise TypeError(
                f"Unsupported value type: {type(value)} -> {value}"
            )

        if section:
            Gaffer.Metadata.registerValue(plug, "layout:section", section)

        node["user"][key] = plug


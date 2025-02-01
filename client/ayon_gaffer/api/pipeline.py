import os
import json

import pyblish.api
from ayon_core.lib import Logger
from ayon_core.pipeline import (register_creator_plugin_path,
                                register_loader_plugin_path)
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

class GafferHost(HostBase, IWorkfileHost, ILoadHost, IPublishHost):
    """
    GafferHost class that integrates with the Gaffer application and provides
    functionalities for workfile management, loading, and publishing.
    """
    name = "gaffer"
    ayon_context = "ayon_context"

    def __init__(self, application):
        """
        Initialize the GafferHost with the given application.
        """
        super(GafferHost, self).__init__()
        self.application = application
        self.application.root()["scripts"].childAddedSignal().connect(
            setup_project, scoped = False)

    def install(self):
        """
        Installs the necessary plugins and registers the host for the pipeline.
        """
        pyblish.api.register_host("gaffer")
        pyblish.api.register_plugin_path(PUBLISH_PATH)

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)

    def close_window(self, script_window):
        """
        Closes the given script window.
        """

        script_window.close()

    def has_unsaved_changes(self):
        """
        Check if there are unsaved changes in the Gaffer script.

        Returns:
            bool: True if there are unsaved changes, False otherwise.
        """
        return GafferScript.node["unsavedChanges"].getValue()

    def get_current_workfile(self):
        """
        Retrieve the current workfile name from the GafferScript node.

        Returns:
            str: The name of the current workfile.
        """
        return GafferScript.node["fileName"].getValue()

    def get_workfile_extensions(self):
        """
        Get the list of workfile extensions.

        Returns:
            list: A list containing the workfile extensions as strings.
        """
        return [".gfr"]

    def open_workfile(self, filepath):
        """
        Opens a workfile in Gaffer.
        Args:
            filepath (str): The path to the workfile to be opened.
        Raises:
            RuntimeError: If the specified file does not exist.
        """
        if not os.path.exists(filepath):
            raise RuntimeError("File does not exist: {}".format(filepath))

        script_window = GafferUI.ScriptWindow.acquire(GafferScript.node)

        GafferUI.FileMenu.addScript(self.application.root(), filepath)
        GafferUI.EventLoop.addIdleCallback(lambda: self.close_window(
            script_window))

    def save_workfile(self, dst_path=None):
        """
        Saves the current workfile to the specified destination path.
        If no destination path is provided, the current workfile path is used.
        The destination path is normalized to use forward slashes.
        """
        if not dst_path:
            dst_path = self.get_current_workfile()

        dst_path = dst_path.replace("\\", "/")

        GafferScript.node.serialiseToFile(dst_path)
        GafferScript.node["fileName"].setValue(dst_path)
        GafferScript.node["unsavedChanges"].setValue(False)

        GafferUI.FileMenu.addRecentFile(self.application, dst_path)

    def update_context_data(self, data, changes):
        """
        Updates the context data by converting the given data to a
        JSON string and setting it to a dynamic StringPlug in the user
        plug of the Gaffer script.
        """
        data_str = json.dumps(data)
        self.user_plug = GafferScript.node["user"]
        self.user_plug[self.ayon_context] = Gaffer.StringPlug(
            defaultValue=data_str,
            flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
        )

    def get_context_data(self):
        """
        Retrieves context data from the user plug in the Gaffer script node.
        """
        self.user_plug = GafferScript.node["user"]
        if self.ayon_context in self.user_plug:
            data_str = self.user_plug[self.ayon_context].getValue()
            return json.loads(data_str)

        return {}

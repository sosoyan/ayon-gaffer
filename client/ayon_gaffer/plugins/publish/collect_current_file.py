import pyblish.api

from ayon_core.lib import get_version_from_path
from ayon_gaffer.api import GafferScript


class CollectCurrentScriptGaffer(pyblish.api.ContextPlugin):
    """Collect current Gaffer script"""

    order = pyblish.api.CollectorOrder - 0.4
    label = "Collect Current Script"
    hosts = ["gaffer"]

    def process(self, context):
        """Collect all image sequence tools"""

        assert GafferScript.get_node(), "Must have active Gaffer script"
        context.data["currentScript"] = GafferScript.get_node()
        self.log.info(f"Collected currentScript:[{GafferScript.get_node()}],")

        # Store path to current file
        filepath = GafferScript.get_node()["fileName"].getValue()
        context.data['currentFile'] = filepath
        self.log.info(f"Collected currentFile:[{filepath}],")

        # Store the version
        context.data["version"] = get_version_from_path(filepath)
        self.log.info(f"Collected version:[{context.data['version']}],")



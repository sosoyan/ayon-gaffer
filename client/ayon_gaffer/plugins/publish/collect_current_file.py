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

        assert GafferScript.node, "Must have active Gaffer script"
        context.data["currentScript"] = GafferScript.node
        self.log.info(f"Collected currentScript:[{GafferScript.node}],")

        # Store path to current file
        filepath = GafferScript.node["fileName"].getValue()
        context.data['currentFile'] = filepath
        self.log.info(f"Collected currentFile:[{filepath}],")

        # Store the version
        context.data["version"] = get_version_from_path(filepath)
        self.log.info(f"Collected version:[{context.data['version']}],")



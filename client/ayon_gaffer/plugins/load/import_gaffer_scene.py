

from ayon_core.lib import BoolDef

from ayon_gaffer.api.lib import (GafferScript, make_box)
from ayon_gaffer.api.plugin import GafferLoaderBase

import Gaffer


class GafferImportScene(GafferLoaderBase):
    """
    Import a gaffer scene (unmanaged)
    """
    product_types = ["gafferNodes", "workfile"]
    representations = ["gfr"]

    label = "Import Gaffer Scene"
    order = -1
    icon = "code-fork"
    color = "white"

    options = [
        BoolDef(
            "box",
            label="Import into Box",
            default=True
        )
    ]

    def load(self, context, name, namespace, data):

        script = GafferScript.node
        path = self.filepath_from_context(context).replace("\\", "/")

        import_to_box = data.get("box", True)
        if import_to_box:
            parent = make_box(name, inputs=[], outputs=[])
            script.addChild(parent)
        else:
            parent = script

        with Gaffer.UndoScope(script):
            new_children = []

            def get_new_children(_parent, child):
                """Capture new children from import via `childAddedSignal`"""
                new_children.append(child)

            callback = parent.childAddedSignal().connect(  # noqa
                get_new_children, scoped=True
            )
            script.importFile(path, parent=parent, continueOnError=True)

            new_nodes = [child for child in new_children
                         if isinstance(child, Gaffer.Node)]

            # Select new nodes
            selection = script.selection()
            selection.clear()

            if import_to_box:
                selection.add([parent])
            else:
                selection.add(new_nodes)

            del callback

from ayon_core.pipeline import get_representation_path

from ayon_gaffer.api.lib import GafferScript
from ayon_gaffer.api.plugin import (GafferLoaderBase,
                                    imprint_container)

import Gaffer


class GafferLoadReference(GafferLoaderBase):
    """Reference a gaffer scene"""

    product_types = ["gafferNodes"]
    representations = ["gfr"]

    label = "Reference Gaffer Scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        path = self.filepath_from_context(context).replace("\\", "/")

        reference = Gaffer.Reference(name)
        GafferScript.get_node().addChild(reference)
        reference.load(path)

        imprint_container(reference,
                          name=name,
                          namespace=namespace,
                          context=context,
                          loader=self.__class__.__name__)

    def switch(self, container, context):
        self.update(container, context)

    def update(self, container, context):
        path = get_representation_path(context["representation"])
        path = path.replace("\\", "/")

        # This is where things get tricky - do we just remove the node
        # completely and replace it with a new one? For now we do. Preferably
        # however we would have it like a 'reference' so that we can just
        # update the loaded 'box' or 'contents' to the new one.
        node: Gaffer.Reference = container["_node"]
        node.load(path)

        # Update the imprinted representation
        node["user"]["representation"].setValue(
            str(context["representation"]["id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)

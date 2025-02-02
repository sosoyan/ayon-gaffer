from ayon_gaffer.api.lib import make_box
from ayon_gaffer.api import plugin
from ayon_gaffer.api.pipeline import AYON_CONTAINER_ID

import Gaffer


class CreateGafferNodes(plugin.GafferCreatorBase):
    identifier = "io.ayon.creators.gaffer.gaffernodes"
    label = "Gaffer Box"
    product_type = "gafferNodes"
    description = "Export Box node for referencing"
    icon = "gears"

    def _create_node(self,
                     product_name: str,
                     pre_create_data: dict,
                     script: Gaffer.ScriptNode) -> Gaffer.Node:

        if len(self.selected_nodes) > 0:
            box_nodes = [node for node in self.selected_nodes
                         if node.typeName() == "Gaffer::Box"]

            if len(box_nodes) == 1 and len(self.selected_nodes) == 1:
                # we have one and just one box selected. So just mark
                # that for publish
                box_node = box_nodes[0]
                data = self._read(box_node)
                if data.get("id") == AYON_CONTAINER_ID:
                    raise plugin.GafferCreatorError(
                        "This box is already being published!")
            else:
                # we have a mix of other nodes, group 'em up
                box_node = Gaffer.Box.create(script, self.selected_nodes)
                box_node.setName(product_name)
        else:
            box_node = make_box(product_name)
            script.addChild(box_node)

        return box_node

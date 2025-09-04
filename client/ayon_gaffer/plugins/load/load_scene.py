import qargparse

from ayon_core.pipeline import (get_representation_path,
                                get_current_context
)
from ayon_core.lib import filter_profiles

from ayon_gaffer.api.lib import (GafferScript,
                                 node_name_from_template,
                                 make_scene_load_box)
from ayon_gaffer.api.plugin import (GafferLoaderBase,
                                    imprint_container)

import GafferScene


class GafferLoadScene(GafferLoaderBase):
    """Load Scene"""

    product_types = [
        "pointcache",
        "model",
        "usd",
        "look",
        "animation",
        "layout"
    ]
    representations = ["abc", "usd"]

    label = "Load scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    node_name_template = "{folder[name]}"
    template_profiles = []
    simple_loading = {}
    advanced_loading = {}

    @classmethod
    def get_options(cls, *args):
        return [
            qargparse.Enum(
                "load_override",
                help="Override simple/advanced loading",
                items=["<use settings>", "simple", "advanced"],
                default=0
            )
        ]

    def load(self, context, name, namespace, options):
        # Create the Loader with the filename path set

        script = GafferScript.get_node()

        load_override = options.get("load_override", "<use settings>")

        # we need to check how we will load this thing, simple or advanced
        # depending on the override - and then settings
        if load_override != "<use settings>":
            load_mode = load_override
        else:
            if self.advanced_loading.get("enabled", True):
                load_mode = "advanced"
            else:
                load_mode = "simple"

        self.log.info(f"Load mode {load_mode}")
        product_type = context["product"]["productType"]

        if load_mode == "advanced":
            template_profiles = self.advanced_loading["template_profiles"]
            self.log.info("Using advanced loading")
            task_name = get_current_context().get("task_name", "")

            selected_profile = filter_profiles(
                template_profiles,
                {'product_type': product_type, 'task_name': task_name},
                keys_order=['product_type', 'task_name'])

            if selected_profile is None:
                raise RuntimeError(
                    "No profile matches product_type: "
                    f"{product_type} and task_name: {task_name}!")

            node_name_template = selected_profile["node_name_template"]
            resolved_node_name = self._get_node_name(
                node_name_template, context)

            sg_location_template = (selected_profile
                                    ["scenegraph_location_template"])
            aux_transforms = selected_profile["auxiliary_transforms"]
            node = make_scene_load_box(
                script,
                resolved_node_name,
                sg_location_template,
                aux_transforms
            )
        else:
            node = GafferScene.SceneReader()
            node_name = self._get_node_name(
                self.simple_loading["node_name_template"], context)
            node.setName(node_name)

        path = self.filepath_from_context(context).replace("\\", "/")
        node["fileName"].setValue(path)
        script.addChild(node)

        self.set_node_color(node, context)

        imprint_container(node,
                          name=name,
                          namespace=namespace,
                          context=context,
                          loader=self.__class__.__name__)

    def switch(self, container, context):
        self.update(container, context)

    def update(self, container, context):
        representation = context["representation"]
        path = get_representation_path(representation)
        path = path.replace("\\", "/")

        node = container["_node"]
        node["fileName"].setValue(path)

        # Update the imprinted representation
        node["user"]["representation"].setValue(str(representation["id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)

    def _get_node_name(self, node_name, context):
        return node_name_from_template(
            node_name, context)

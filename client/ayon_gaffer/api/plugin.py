import json
import imath
from abc import abstractmethod

from ayon_core.pipeline import (
    Creator as NewCreator,
    CreatedInstance,
    CreatorError,
    load,
)

from ayon_core.lib import (
    BoolDef
)
import ayon_api


from ayon_gaffer.api.lib import GafferScript
from ayon_gaffer.api.pipeline import (
    imprint,
    JSON_PREFIX
)
from ayon_core.pipeline import AYON_INSTANCE_ID
import ayon_gaffer.api.lib


import Gaffer
import imath


def read(node):
    """Read all 'user' custom data on the node"""
    if "user" not in node:
        # No user attributes
        return {}
    return {
        plug.getName(): plug.getValue() for plug in node["user"]
    }


class CreatorImprintReadMixin:
    """Mixin providing _read and _imprint methods to be used by Creators."""

    attr_prefix = "ayon_"
    op_attr_prefix = "openpype_"

    def _read(self, node: Gaffer.Node) -> dict:
        all_user_data = read(node)

        # Consider only data with the special attribute prefix
        # and strip off the prefix as for the resulting data

        ayon_data = {}
        for key, value in all_user_data.items():

            if key.startswith(self.attr_prefix):
                prefix_len = len(self.attr_prefix)
            elif key.startswith(self.op_attr_prefix):
                prefix_len = len(self.op_attr_prefix)
            else:
                continue

            if isinstance(value, str) and value.startswith(JSON_PREFIX):
                value = value[len(JSON_PREFIX):]  # strip off JSON prefix
                value = json.loads(value)
            elif isinstance(value, str) and value == "<None>":
                value = None

            key = key[prefix_len:]      # strip off prefix
            ayon_data[key] = value

        ayon_data["instance_id"] = node.fullName()

        if "creator_identifier" in ayon_data.keys():
            # if we have an openpye creator identifier, let's temporarily
            # make it an ayon one.
            creator_id = ayon_data["creator_identifier"]
            if ".openpype." in creator_id:
                ayon_data["creator_identifier"] = creator_id.replace(
                    ".openpype.", ".ayon.")

        return ayon_data

    def _imprint(self, node: Gaffer.Node, data: dict):
        # Instance id is the node's unique full name so we don't need to
        # imprint as data. This makes it so that duplicating a node will
        # correctly detect it as a new unique instance.
        data.pop("instance_id", None)

        # Prefix all keys
        ayon_data = {}
        for key, value in data.items():
            key = f"{self.attr_prefix}{key}"
            ayon_data[key] = value

        imprint(node, ayon_data)


class GafferCreatorError(CreatorError):
    pass


class GafferCreatorBase(NewCreator, CreatorImprintReadMixin):
    """Base class for single node Creators in Gaffer.

    Child classes must implement `_create_node` to define the node to be
    Created. Aside of that everything should already be handled by the base
    class but can be overridden for special cases.

    """
    default_variants = ["Main"]
    selected_nodes = []

    @abstractmethod
    def _create_node(self,
                     product_name: str,
                     pre_create_data: dict) -> Gaffer.Node:
        """Create the relevant node type for the instance.

        This only gets called on Create, update is handled automatically by
        updating imprinted data on this node.

        Arguments:
            product_name (str): The product name to be created. Usually used for
                the node's name.
            pre_create_data (dict): The `pre_create_data` of the `create` call
                of this Creator.

        Returns:
            Gaffer.Node: The created node.

        """
        pass

    def set_selected_nodes(self, pre_create_data, script):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = script.selection()
            if len(self.selected_nodes) == 0:
                raise GafferCreatorError("Creator error: No nodes selected")

        else:
            self.selected_nodes = []

    def create_nice_label(self, instance_data):
        product_name = instance_data["productName"]

        folder_path = instance_data["folderPath"]
        return f"{product_name} [{folder_path}]"

    def create(self, product_name, instance_data, pre_create_data):
        instance_data.update({
            "id": AYON_INSTANCE_ID,
            "productName": product_name
        })

        # strip out the task
        instance_data["task"] = None

        script = GafferScript.node
        assert script, "Must have a gaffer scene script as root"

        # populate self.selecte_nodes
        self.set_selected_nodes(pre_create_data, script)

        # Create a box node for publishing
        node = self._create_node(product_name, pre_create_data, script)

        # Register the CreatedInstance
        instance = CreatedInstance(
            product_type=self.product_type,
            product_name=product_name,
            data=instance_data,
            creator=self,
        )
        data = instance.data_to_store()

        self._imprint(node, data)

        # Insert the transient data
        instance.transient_data["node"] = node
        new_label = self.create_nice_label(instance.data)
        instance.data["label"] = new_label

        node.setName(
            f"{product_name}_{instance.data['folderPath'].split('/')[-1]}")

        self._add_instance_to_context(instance)

        return instance

    def collect_instances(self):

        script = GafferScript.node
        assert script, "Must have a gaffer scene script as root"
        if hasattr(self, "deprecated_identifiers"):
            identifiers = [self.identifier] + self.deprecated_identifiers
        else:
            identifiers = [self.identifier]
        for node in script.children(Gaffer.Node):
            data = self._read(node)
            if data.get("creator_identifier") not in identifiers:
                continue

            # TODO: I need to understand better how tasks work after the
            # ayon_core move
            # if there is not task, we need it to be None, instead of ""
            task = data.get("task")
            if task is not None and task == "":
                data["task"] = None
            # Add instance
            created_instance = CreatedInstance.from_existing(data, self)

            # Collect transient data
            created_instance.transient_data["node"] = node
            new_label = self.create_nice_label(created_instance.data)
            created_instance.data["label"] = new_label
            # new_label = f"{product_name} [{folder_path.split('/')[-1]}]"
            # instance.data["label"] = new_label

            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            new_data = created_inst.data_to_store()
            box = created_inst.transient_data["node"]
            self._imprint(box, new_data)

    def remove_instances(self, instances):
        for instance in instances:
            # Remove the tool from the scene

            node = instance.transient_data["node"]
            if node:
                parent = node.parent()
                parent.removeChild(node)
                del node

            # Remove the collected CreatedInstance to remove from UI directly
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef(
                "use_selection",
                default=False,
                label="Use selection"
            )
        ]


class GafferRenderCreator(NewCreator, CreatorImprintReadMixin):
    """Creator which creates an instance per renderlayer upstream from each
    publish job nodes

    Child classes must implement `_create_node` to define the node to be
    Created. Aside of that everything should already be handled by the base
    class but can be overridden for special cases.

    """
    default_variants = ["Main"]
    selected_nodes = []

    @abstractmethod
    def _create_node(self,
                     product_name: str,
                     pre_create_data: dict) -> Gaffer.Node:
        """Create the relevant node type for the instance.

        This only gets called on Create, update is handled automatically by
        updating imprinted data on this node.

        Arguments:
            product_name (str): The product name to be created. Usually used
                for the node's name.
            pre_create_data (dict): The `pre_create_data` of the `create` call
                of this Creator.

        Returns:
            Gaffer.Node: The created node.

        """
        pass

    def create(self, product_name, instance_data, pre_create_data):
        self.log.info('create()')
        instance_data.update({
            "id": AYON_INSTANCE_ID,
            "productName": product_name
        })

        script = GafferScript.node
        assert script, "Must have a gaffer scene script as root"

        # Create a box node for publishing
        node = self._create_node(product_name, pre_create_data, script)

        # add an annotation to highlight where this is publishing to
        Gaffer.Metadata.registerValue(
            node,
            "annotation:user:text",
            instance_data["folderPath"]
        )
        Gaffer.Metadata.registerValue(
            node,
            "annotation:user:color",
            imath.Color3f(0.150000006, 0.25999999, 0.25999999)
        )
        # Register the CreatedInstance
        instance = CreatedInstance(
            product_type=self.product_type,
            product_name=product_name,
            data=instance_data,
            creator=self,
        )
        data = instance.data_to_store()
        self._imprint(node, data)

        # Insert the transient data
        instance.transient_data["node"] = node

        # self._add_instance_to_context(instance)

        # return instance
        self.collect_instances()

    def collect_instances(self):
        self.log.info('Collecting instances!')
        script = GafferScript.node
        assert script, "Must have a gaffer scene script as root"

        if hasattr(self, "deprecated_identifiers"):
            identifiers = [self.identifier] + self.deprecated_identifiers
        else:
            identifiers = [self.identifier]
        for publish_node in script.children(AyonPublishTask):
            data = self._read(publish_node)
            if data.get("creator_identifier") not in identifiers:
                self.log.info("{} - {}".format(
                    data.get("creator_identifier"), self.identifier))
                self.log.debug(f'Skipping {publish_node}, wrong creator id')
                continue

            layers = Gaffer.NodeAlgo.upstreamNodes(
                publish_node,
                RenderLayerNode
            )

            for layer in layers:
                layer_name = layer['layer_name'].getValue().strip()

                project_name = self.create_context.get_current_project_name()
                layer_data = self._read(layer)
                if layer_data.get("folderPath") is None:
                    # we need to create the instance data for this layer

                    folder_path = data["folderPath"]
                    instance_data = {
                        "task": data["task"],
                        "variant": layer_name,
                    }
                    instance_data["folderPath"] = folder_path
                    folder = ayon_api.get_folder_by_path(
                        project_name, folder_path)
                    task_entity = ayon_api.get_task_by_name(
                        project_name, folder["id"], instance_data["task"]
                    )
                    product_name = self.get_product_name(
                        project_name,
                        folder,
                        task_entity,
                        layer_name,
                        )

                    instance = CreatedInstance(
                        product_type=self.product_type,
                        product_name=product_name,
                        data=instance_data,
                        creator=self
                    )
                else:
                    instance = CreatedInstance.from_existing(layer_data, self)
                    # we want the folder path from the publish node, that the
                    # renderlayer is connected into
                    folder_path = data["folderPath"]
                    folder = ayon_api.get_folder_by_path(
                        project_name, folder_path)
                    task_entity = ayon_api.get_task_by_name(
                        project_name, folder["id"], layer_data["task"],)
                    product_name = self.get_product_name(
                        project_name,
                        folder,
                        task_entity,
                        layer_name,
                    )
                    instance.data["variant"] = layer_name
                instance.transient_data["node"] = layer
                instance.transient_data["parent_publish_node"] = publish_node

                new_label = f"{product_name} [{folder_path}]"

                instance.data["label"] = new_label
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for instance, _changes in update_list:
            the_node = instance.transient_data["node"]
            new_data = instance.data_to_store()

            # we remove some data, since that is set on the publish node
            # and it makes no sense to be able to change one shot for all
            # layers 
            for key in ["folderPath", "task"]:
                del new_data[key]

            self._imprint(the_node, new_data)

    def remove_instances(self, instances):
        pub_nodes_to_remove = []
        for instance in instances:
            # Remove the tool from the scene

            node = instance.transient_data["parent_publish_node"]
            pub_nodes_to_remove.append(node)

        for instance in list(self.create_context.instances):
            if instance.get('creator_identifier') == self.identifier:
                pub_node = instance.transient_data["parent_publish_node"]
                if pub_node in pub_nodes_to_remove:
                    self._remove_instance_from_context(instance)

        for pub_node in pub_nodes_to_remove:
            parent = node.parent()
            parent.removeChild(node)
            del node


class PlugSettingsMixin:

    def apply_plug_settings(self, node):
        print("Applygin plug from settings")
        for plug in self.plugs:
            plug_name = plug["name"]
            plug_type = plug["type"]
            plug_value = plug[plug_type]

            print(f"* {plug_name}")

            # now let's find the actual plug
            plug_path = plug_name.split(".")
            try:
                target_plug = node
                for pp in plug_path:
                    target_plug = target_plug[pp]
            except KeyError:
                print(f"No plug [{plug_path}] for node {node}")
                continue

            if plug_type in ["text", "boolean", "number", "decimal"]:
                print(f"Setting [{target_plug}] to [{plug_value}]")
                pass  # we just pass plug_value on as-is

            elif plug_type == "v2f":
                plug_value = imath.V2f(plug_value["x"], plug_value["y"])
            elif plug_type == "v3f":
                plug_value = imath.V2f(
                        plug_value["x"], plug_value["y"], plug_value["z"])
            elif plug_type == "color3f":
                plug_value = imath.Color3f(
                        plug_value["r"], plug_value["g"], plug_value["b"])
            elif plug_type == "color4f":
                plug_value = imath.Color4f(
                        plug_value["r"],
                        plug_value["g"],
                        plug_value["b"],
                        plug_value["a"])
            try:
                target_plug.setValue(plug_value)
            except Exception as err:
                print(f"ERROR: {err}")


class GafferLoaderBase(load.LoaderPlugin):
    def set_node_color(self, node, context):
        product_type = context["product"].get("productType", "")
        ayon_gaffer.api.lib.set_node_color_from_settings(node, product_type)

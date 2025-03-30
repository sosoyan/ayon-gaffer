
import ast
import platform
import ayon_api

from ayon_core.lib import Logger
from ayon_gaffer.api.lib import GafferScript

import IECore
import Gaffer
import GafferScene


log = Logger.get_logger(__name__)

def eval_str(value):
    sub_value = GafferScript.node.context().substitute(value)

    if sub_value:
        return sub_value
    else:
        return value

def select_preset(plug, prereload_name):
    prereload_value = Gaffer.Metadata.value(plug, f"preset:{prereload_name}")
    if prereload_value is not None:
        plug.setValue(prereload_value)
    else:
        log.error(f"Preset '{prereload_name}' not found!")

def get_project_names():
    return ayon_api.get_project_names()

def get_project_roots(project_name):
    return ayon_api.get_project_roots_by_platform(
        project_name,
        platform.system().lower())

def get_product_types(project_name, folder_path):
    folder_id = ayon_api.get_folder_by_path(project_name, folder_path)["id"]
    products = ayon_api.get_products(project_name, folder_ids=[folder_id])

    product_types = list(set(
        product['productType'] for product in list(products)))

    return product_types

def get_product_names(project_name, folder_path, product_type):
    folder_id = ayon_api.get_folder_by_path(project_name, folder_path)["id"]
    products = ayon_api.get_products(project_name, folder_ids=[folder_id])

    product_names = [i for i in products if
                    i['productType'] == product_type]

    return product_names

def get_product_versions(project_name, product_id):
    versions = ayon_api.get_versions(project_name, product_ids=[product_id])
    return list(versions)

def get_representations(project_name, version_id):
    representations = ayon_api.get_representations(
        project_name,
        version_ids=[version_id],
        fields=["files"])

    return list(representations)

def version_picker(status):
    status_priority = {
        "Reference": 1,
        "Rejected": 2,
        "Not Ready": 3,
        "Pending Review": 4,
        "In Progress": 5,
        "Approved": 6
    }

    return status_priority.get(status, 0)

class ProductReaderSerialiser(Gaffer.NodeSerialiser):
    """
    Ayon Reader Serializer
    """
    def childNeedsSerialisation(self, child, serialisation):
        """
        Implementation of native method
        @param child: Reader
        @param serialisation: Gaffer.Serialisation
        @return: 
        """
        if isinstance(child, Gaffer.Node):
            return True

        return Gaffer.NodeSerialiser.childNeedsSerialisation(self,
                                                             child,
                                                             serialisation)

    def childNeedsConstruction(self, child, serialisation):
        """
        Implementation of native method
        @param child: ProductReader
        @param serialisation: Gaffer.Serialisation
        @return:
        """
        if isinstance(child, Gaffer.Node):
            return True

        return Gaffer.NodeSerialiser.childNeedsConstruction(self,
                                                            child,
                                                            serialisation)

class ProductReader(GafferScene.SceneNode):

    def __init__(self, name="ProductReader"):

        GafferScene.SceneNode.__init__(self, name)

        self.addChild(Gaffer.IntPlug("reload",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("projectName",
                                        Gaffer.Plug.Direction.In,
                                        "${ayon:projectName}"))
        self.addChild(Gaffer.StringPlug("folderPath",
                                        Gaffer.Plug.Direction.In,
                                        "${ayon:folderPath}"))
        self.addChild(Gaffer.StringPlug("productType",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("productName",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("productVersion",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("representation",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("projectRoot",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("filePath",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("refreshCount",
                                     Gaffer.Plug.Direction.In))

        self.addChild(Gaffer.TransformPlug("transform",
                                           Gaffer.Plug.Direction.In))

        self["sceneReader"] = GafferScene.SceneReader()
        self["sceneReader"]["fileName"].setInput(self["filePath"])
        self["sceneReader"]['refreshCount'].setInput(self["refreshCount"])
        self["sceneReader"]["transform"].setInput(self["transform"])

        self["out"].setInput(self["sceneReader"]["out"])

        self.plugSetSignal().connect(self.plug_set, scoped=False)

        Gaffer.Metadata.registerValue(self["transform"],
                                      "layout:section",
                                      "Transform")

        self.reload_all()

    def affects(self, input):
        affected = super(ProductReader, self).affects(input)

        if input == self["filePath"]:
            affected.append(self["sceneReader"]["fileName"])

        elif input == self["refreshCount"]:
            affected.append(self["sceneReader"]["refreshCount"])

        return affected

    def hash(self, output, context, h):
        h.append(self["filePath"].hash())
        h.append(self['reload'].hash())

    def plug_set(self, plug):
        if(plug.getName() == "projectName"):
            self.reload_product_types()
            self.reload_product_names()
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()
        elif(plug.getName() == "folderPath"):
            self.reload_product_types()
            self.reload_product_names()
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()
        elif(plug.getName() == "productType"):
            self.reload_product_names()
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()
        elif(plug.getName() == "productName"):
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()
        elif(plug.getName() == "productVersion"):
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()
        elif(plug.getName() == "representation"):
            self.reload_resolved_path()
        elif(plug.getName() == "reload"):
            self.reload_all()

    def register_plug_presetes(self, plug, name, value):
        Gaffer.Metadata.registerPlugValue(plug, "preset:" + name, value)

    def deregister_plug_presetes(self, plug):
        metadata_keys = Gaffer.Metadata.registeredValues(plug)

        for key in metadata_keys:
            if key.startswith("preset:"):
                Gaffer.Metadata.deregisterValue(plug, key)

    def reload_all(self):
        self.reload_project_names()
        self.reload_folder_path()
        self.reload_product_types()
        self.reload_product_names()
        self.reload_product_versions()
        self.reload_representations()
        self.reload_project_roots()
        self.reload_resolved_path()

    def reload_project_names(self):
        self.deregister_plug_presetes(self["projectName"])
        project_names = ["${ayon:projectName}"] + get_project_names()

        for name in project_names:
            self.register_plug_presetes(self["projectName"], name, name)

    def reload_folder_path(self):
        self["folderPath"].setValue("${ayon:folderPath}")

    def reload_product_types(self):
        self.deregister_plug_presetes(self["productType"])

        project_name = eval_str(self["projectName"].getValue())

        folder_path = eval_str(self["folderPath"].getValue())
        product_types = get_product_types(project_name, folder_path)

        for i, p_type in enumerate(product_types):
            self.register_plug_presetes(self["productType"], p_type, p_type)

            if i == 0:
                select_preset(self["productType"], p_type)

    def reload_product_names(self):
        self.deregister_plug_presetes(self["productName"])

        project_name = eval_str(self["projectName"].getValue())
        folder_path = eval_str(self["folderPath"].getValue())
        product_type = eval_str(self["productType"].getValue())

        product_names = get_product_names(
            project_name,
            folder_path,
            product_type)

        for i, product in enumerate(product_names):
            self.register_plug_presetes(
                self["productName"],
                product["name"],
                str(product))

            if i == 0:
                select_preset(self["productName"], product["name"])

    def reload_product_versions(self):
        self.deregister_plug_presetes(self["productVersion"])

        project_name = eval_str(self["projectName"].getValue())
        product_id = ast.literal_eval(self["productName"].getValue())["id"]
        versions = get_product_versions(project_name, product_id)

        picked_status = 0

        for version in versions:
            self.register_plug_presetes(
                self["productVersion"],
                f"{version['name']} ({version['status']})",
                str(version))

            current_status = version_picker(version["status"])

            if picked_status >= current_status:
                picked_status = current_status
                select_preset(self["productVersion"],
                              f"{version['name']} ({version['status']})")

    def reload_representations(self):
        self.deregister_plug_presetes(self["representation"])

        project_name = eval_str(self["projectName"].getValue())
        version_id = ast.literal_eval(self["productVersion"].getValue())["id"]
        representations = get_representations(
            project_name,
            version_id)

        for i, repr in enumerate(representations):
            self.register_plug_presetes(
                self["representation"],
                repr["files"][0]["name"],
                str(repr["files"][0]))

            if i == 0:
                select_preset(self["representation"],
                              repr["files"][0]["name"])

    def reload_project_roots(self):
        self.deregister_plug_presetes(self["projectRoot"])

        project_name = eval_str(self["projectName"].getValue())
        project_roots = get_project_roots(project_name)

        for i, (key, value) in enumerate(project_roots.items()):
            self.register_plug_presetes(self["projectRoot"], key, value)

            if i == 0:
                select_preset(self["projectRoot"], key)

    def reload_resolved_path(self):
        path = ast.literal_eval(self["representation"].getValue())["path"]

        start = path.find("{")
        end = path.find("}")

        if start != -1 and end != -1:
            root = self["projectRoot"].getValue()
            resolved_path = path[:start] + root + path[end + 1:]

            self["filePath"].setValue(resolved_path)

IECore.registerRunTimeTyped(ProductReader, typeName="AyonProductReader")

Gaffer.Metadata.registerNode(
    ProductReader,
    "description", "Ayon Product Reader",
    "graphEditor:childrenViewable", True,
    plugs={
         "projectName": [
             "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "projectRoot": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productType": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productName": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productVersion": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "representation": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "refreshCount": [
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],
        "reload": [
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget"]
        }
    )

Gaffer.Serialisation.registerSerialiser(ProductReader,
                                        ProductReaderSerialiser())

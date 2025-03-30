
import ast
import platform
import ayon_api

from ayon_core.lib import Logger

from ayon_gaffer.api.lib import GafferScript

import IECore
import Gaffer
import GafferScene


log = Logger.get_logger(__name__)

def ver_str(ver):
    return f"v{ver:03d}"

def eval_str(value):
    sub_value = GafferScript.node.context().substitute(value)

    if sub_value:
        return sub_value
    else:
        return value

def replace_curly_braces(path, replacement_string):

    start = path.find("{")
    end = path.find("}")

    if start != -1 and end != -1:
        path = path[:start] + replacement_string + path[end + 1:]

    return path

def select_preset(plug, preset_name):
    preset_value = Gaffer.Metadata.value(plug, f"preset:{preset_name}")
    if preset_value is not None:
        plug.setValue(preset_value)
    else:
        print(f"Preset '{preset_name}' not found!")

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
    """
    Ayon Reader Node
    """
    def __init__(self, name="ProductReader"):
        """
        @param name: str
        """
        GafferScene.SceneNode.__init__(self, name)

        # Status string
        self.status = str()
        self.tmp = IECore.StringVectorData(["assd", "asdsdsdad"])

        self["projectName"] = Gaffer.StringPlug(
            defaultValue="${ayon:projectName}"
            )
        self["folderPath"] = Gaffer.StringPlug(
            defaultValue="${ayon:folderPath}"
            )
        self["productType"] = Gaffer.StringPlug()
        self["productName"] = Gaffer.StringPlug()
        self["productVersion"] = Gaffer.StringPlug()
        self["respresentation"] = Gaffer.StringPlug()
        self["projectRoot"] = Gaffer.StringPlug()
        self["resolvedPath"] = Gaffer.StringPlug()
        self["refresh"] = Gaffer.IntPlug()

        self.scene_reader = GafferScene.SceneReader()
        self.scene_reader["fileName"].setInput(self["resolvedPath"])
        self.addChild(self.scene_reader)

        self["out"] = GafferScene.ScenePlug("out", Gaffer.Plug.Direction.Out)
        self["out"].setInput(self.scene_reader["out"])

        self.refresh_context()

        self.plugSetSignal().connect(self.plug_set, scoped=False)

    def register_plug_presetes(self, plug, name, value):
        Gaffer.Metadata.registerPlugValue(plug, "preset:" + name, value)

    def deregister_plug_presetes(self):
        for plug in self.children():
            if isinstance(plug, Gaffer._Gaffer.StringPlug):
                metadata_keys = Gaffer.Metadata.registeredValues(plug)

                for key in metadata_keys:
                    if key.startswith("preset:"):
                        Gaffer.Metadata.deregisterValue(plug, key)

    def refresh_context(self):
        self.deregister_plug_presetes()

        # Set project names
        for name in get_project_names():
            self.register_plug_presetes(self["projectName"], name, name)

        project_name = eval_str(self["projectName"].getValue())

        # Set product types
        folder_path = eval_str(self["folderPath"].getValue())
        product_types = get_product_types(project_name, folder_path)

        for i, p_type in enumerate(product_types):
            self.register_plug_presetes(self["productType"], p_type, p_type)

            if i == 0:
                select_preset(self["productType"], p_type)

        # Set product names
        product_type = eval_str(self["productType"].getValue())
        pproduct_names = get_product_names(
            project_name,
            folder_path,
            product_type)

        for i, product in enumerate(pproduct_names):
            self.register_plug_presetes(
                self["productName"],
                product["name"],
                str(product))

            if i == 0:
                select_preset(self["productName"], product["name"])

        # Set product versions
        product_id = ast.literal_eval(self["productName"].getValue())["id"]
        versions = get_product_versions(project_name, product_id)

        for i, version in enumerate(versions):
            self.register_plug_presetes(
                self["productVersion"],
                ver_str(version["version"]),
                str(version))

            if i == len(versions) - 1:
                select_preset(self["productVersion"],
                              ver_str(version["version"]))

        # Set representations
        version_id = ast.literal_eval(self["productVersion"].getValue())["id"]
        representations = get_representations(
            project_name,
            version_id)

        for repr in representations:
            self.register_plug_presetes(
                self["respresentation"],
                repr["files"][0]["name"],
                str(repr["files"][0]))

            if i == 0:
                select_preset(self["respresentation"],
                              repr["files"][0]["name"])

        # Set project roots
        project_roots = get_project_roots(project_name)

        for i, (key, value) in enumerate(project_roots.items()):
            self.register_plug_presetes(self["projectRoot"], key, value)

            if i == 0:
                select_preset(self["projectRoot"], key)

        # Set resolved path
        resolved_path = ast.literal_eval(
            self["respresentation"].getValue())["path"]
        resolved_path = replace_curly_braces(resolved_path,
                                             self["projectRoot"].getValue())

        self["resolvedPath"].setValue(resolved_path)

    def hash(self, output, context, h):
        """
        Implementation of native method
        @param output: Gaffer.Plug
        @param context: Gaffer.Context
        @param h: IECore.MurmurHash
        @return: None
        """
        h.append(self["projectName"].hash())
        h.append(self["projectRoot"].hash())
        h.append(self["folderPath"].hash())
        h.append(self["productType"].hash())
        h.append(self["productName"].hash())
        h.append(self["Version"].hash())


    def hashCachePolicy(self, output):
        """
        Implementation of native method
        @param output: Gaffer.Plug
        @return: Gaffer.ValuePlug.CachePolicy
        """
        return Gaffer.ValuePlug.CachePolicy.Uncached

    def compute(self, output, context):
        """
        Implementation of native method
        @param output: Gaffer.Plug
        @param context: Gaffer.Context
        @return:
        """
        print("Compute: ", output.getName())
        if output.getName() == "status":
            output.setValue(self.status)

    def plug_set(self, plug):
        """
        Sets plug value
        @param plug: Gaffer.Plug
        @return: None
        """
        print("Plug set: ", plug.getName())

IECore.registerRunTimeTyped(ProductReader, typeName="AyonProductReader")

Gaffer.Metadata.registerNode(
    ProductReader,
    "description", "Ayon Product Reader",
    "graphEditor:childrenViewable", True,
    plugs={
         "projectName": [
             "preset:${ayon:projectName}", "${ayon:projectName}",
             "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "projectRoot": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "folderPath": [
            "preset:${ayon:folderPath}", "${ayon:folderPath}"],

        "productType": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productName": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productVersion": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "respresentation": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "refresh": [
            "plugValueWidget:type", "GafferUI.ButtonPlugValueWidget"]
        }
    )

Gaffer.Serialisation.registerSerialiser(ProductReader, ProductReaderSerialiser())

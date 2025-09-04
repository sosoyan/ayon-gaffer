import ast
import platform
from enum import IntFlag
from pathlib import Path

import ayon_api
import ayon_api.exceptions

from ayon_core.lib import Logger
from ayon_gaffer.api.lib import GafferScript
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path)

import imath
import Gaffer
import IECore


log = Logger.get_logger(__name__)

GAFFER_HOST_DIR = Path(__file__).resolve().parents[2].as_posix()

def select_preset(plug, preset):
    preset_value = Gaffer.Metadata.value(plug, f"preset:{preset}")
    if preset_value is not None:
        plug.setValue(preset_value)
    else:
        log.error(f"Preset '{preset}' not found!")

def plug_presets_exists(plug, presets):
    existing_presets = [
        value.removeprefix("preset:")
        for value in Gaffer.Metadata.registeredValues(plug)
        if value.startswith("preset:")
    ]
    return existing_presets == presets

def plug_values_exists(plug, values):
    existing_values = []

    for preset in Gaffer.Metadata.registeredValues(plug):
        if preset.startswith("preset:"):
            existing_values.append(Gaffer.Metadata.value(plug, preset))

    return existing_values == values

def get_project_names():
    return ayon_api.get_project_names()

def get_project_roots(project_name):
    if project_name:
        return ayon_api.get_project_roots_by_platform(
            project_name,
            platform.system().lower())

def get_products(project_name, folder_path):
    try:
        folder = ayon_api.get_folder_by_path(project_name, folder_path)
    except ayon_api.exceptions.GraphQlQueryFailed:
        pass

    if folder is not None:
        folder_id = folder.get("id")
        return ayon_api.get_products(project_name, folder_ids=[folder_id])

    return []

def get_product_types(project_name, folder_path, filter=[]):
    if project_name and folder_path:
        products = get_products(project_name, folder_path)
        product_types = list(set(
            product['productType'] for product in list(products)))

        if filter:
            product_types = [i for i in product_types if i in filter]

        if not product_types:
            log.error(
                ("Can't find product types with filter"
                f"{filter} at '{project_name}{folder_path}'"))

        return product_types

def get_product_names(project_name, folder_path, product_type):
    if project_name and folder_path and product_type:
        products = get_products(project_name, folder_path)
        product_names = [i for i in products if
                        i['productType'] == product_type]

        if not product_names:
            log.error(
                f"Can't find product names at '{project_name}{folder_path}'")

        return product_names

def get_product_versions(project_name, product_id):
    if project_name and product_id:
        versions = ayon_api.get_versions(project_name, product_ids=[product_id])

        if not versions:
            log.error(
                f"Can't find product versions for product id: '{product_id}'")

        return list(versions)

def get_representations(project_name, version_id):
    if project_name and version_id:
        representations = ayon_api.get_representations(
            project_name,
            version_ids=[version_id],
            fields=["files"])

        return list(representations)

class ReloadFlag(IntFlag):
    PROJECT_NAME = 0x0002
    FOLDER_PATH = 0x0004
    PRODUCT_TYPE = 0x0008
    PRODUCT_NAME = 0x0010
    PRODUCT_VERSION = 0x0020
    REPRESENTATION = 0x0040
    PROJECT_ROOT = 0x0080
    FILE_NAME = 0x0100

    ALL = (
        PROJECT_NAME
        | FOLDER_PATH
        | PRODUCT_TYPE
        | PRODUCT_NAME
        | PRODUCT_VERSION
        | REPRESENTATION
        | PROJECT_ROOT
        | FILE_NAME
    )

    PRODUCT_TYPE_DOWNWARD = (
        PRODUCT_TYPE
        | PRODUCT_NAME
        | PRODUCT_VERSION
        | REPRESENTATION
        | PROJECT_ROOT
        | FILE_NAME
    )
    PRODUCT_NAME_DOWNWARD = (
        PRODUCT_NAME
        | PRODUCT_VERSION
        | REPRESENTATION
        | PROJECT_ROOT
        | FILE_NAME
    )
    PRODUCT_VERSION_DOWNWARD = (
        PRODUCT_VERSION
        | REPRESENTATION
        | PROJECT_ROOT
        | FILE_NAME
    )
    REPRESENTATION_DOWNWARD = (
        REPRESENTATION
        | PROJECT_ROOT
        | FILE_NAME
    )
    PROJECT_ROOT_DOWNWARD = (
        PROJECT_ROOT
        | FILE_NAME
    )

class ProductReader(Gaffer.Box):

    def __init__(self, name="ProductReader"):

        Gaffer.Box.__init__(self, name)

        self.current = "current context"
        self.custom = "custom"
        self.type_filter =[]
        self.file_name = ""

        self.addChild(Gaffer.IntPlug("reloadAll",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("projectName",
                                        Gaffer.Plug.Direction.In,
                                        self.current))
        self.addChild(Gaffer.IntPlug("reloadProjectName",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("folderPath",
                                        Gaffer.Plug.Direction.In,
                                        self.current))
        self.addChild(Gaffer.IntPlug("reloadFolderPath",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("folderPathCustom",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadFolderPathCustom",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("productType",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadProductType",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("productName",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadProductName",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("productVersion",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadProductVersion",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("representation",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadRepresentation",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("projectRoot",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("reloadProjectRoot",
                                     Gaffer.Plug.Direction.In)),
        self.addChild(Gaffer.StringPlug("fileName",
                                        Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.IntPlug("refreshCount",
                                     Gaffer.Plug.Direction.In))

        self.plugSetSignal().connect(self.plug_set, scoped=False)

        self.reload()

    def plug_set(self, plug):

        if plug.getName() in ["reloadAll",
                              "reloadProjectName"]:
            self.reload()

        elif plug.getName() in ["projectName",
                                "folderPath",
                                "reloadFolderPath",
                                "folderPathCustom",
                                "reloadFolderPathCustom",
                                "reloadProductType"]:

            self.reload(ReloadFlag.PRODUCT_TYPE_DOWNWARD)

        elif plug.getName() in ["productType", "reloadProductName"]:
            self.reload(ReloadFlag.PRODUCT_NAME_DOWNWARD)

        elif plug.getName() in ["productName", "reloadProductVersion"]:
            self.reload(ReloadFlag.PRODUCT_VERSION_DOWNWARD)

        elif plug.getName() in ["productVersion", "reloadRepresentation"]:
            self.reload(ReloadFlag.REPRESENTATION_DOWNWARD)

        elif plug.getName() in ["representation", "reloadProjectRoot"]:
            self.reload(ReloadFlag.PROJECT_ROOT_DOWNWARD)

        elif plug.getName() in ["projectRoot", "refreshCount"]:
            self.reload(ReloadFlag.FILE_NAME)

    def register_plug_preset(self, plug, name, value):
        Gaffer.Metadata.registerPlugValue(plug, "preset:" + name, value)

    def deregister_plug_presetes(self, plug):
        metadata_keys = Gaffer.Metadata.registeredValues(plug)

        for key in metadata_keys:
            if key.startswith("preset:"):
                Gaffer.Metadata.deregisterValue(plug, key)

    def get_project_name(self):
        project_name = self["projectName"].getValue()

        script_node = GafferScript.get_node()

        if script_node:
            script_variables = script_node["variables"]

            if (project_name == self.current):
                return script_variables["ayon:projectName"]["value"].getValue()

            return project_name

    def get_folder_path(self):
        folder_path = self["folderPath"].getValue()
        
        script_node = GafferScript.get_node()

        if script_node:
            script_variables = script_node["variables"]

            if (folder_path == self.current):
                Gaffer.Metadata.registerValue(
                    self["folderPathCustom"], "plugValueWidget:type", "")
                Gaffer.Metadata.registerValue(
                    self["reloadFolderPathCustom"], "plugValueWidget:type", "")

                return script_variables["ayon:folderPath"]["value"].getValue()

            Gaffer.Metadata.registerValue(
                    self["folderPathCustom"],
                    "plugValueWidget:type",
                    "GafferUI.StringPlugValueWidget")
            Gaffer.Metadata.registerValue(
                    self["reloadFolderPathCustom"],
                    "plugValueWidget:type",
                    "GafferUI.RefreshPlugValueWidget")

        return self["folderPathCustom"].getValue()

    def reload(self, flag=ReloadFlag.ALL):

        if flag & ReloadFlag.PROJECT_NAME:
            self.reload_project_names()
        if flag & ReloadFlag.FOLDER_PATH:
            self.reload_folder_path()
        if flag & ReloadFlag.PRODUCT_TYPE:
            self.reload_product_types()
        if flag & ReloadFlag.PRODUCT_NAME:
            self.reload_product_names()
        if flag & ReloadFlag.PRODUCT_VERSION:
            self.reload_product_versions()
        if flag & ReloadFlag.REPRESENTATION:
            self.reload_representations()
        if flag & ReloadFlag.PROJECT_ROOT:
            self.reload_project_roots()
        if flag & ReloadFlag.FILE_NAME:
            self.reload_file_name()

    def reload_project_names(self):

        project_names = [self.current] + get_project_names()

        if not plug_presets_exists(
            self["projectName"],
            project_names):

            selected = self["projectName"].getValue()
            self.deregister_plug_presetes(self["projectName"])

            for name in project_names:
                self.register_plug_preset(self["projectName"], name, name)

            if selected in project_names:
                select_preset(self["projectName"], selected)
            else:
                select_preset(self["projectName"], self.current)

    def reload_folder_path(self):
        self["folderPath"].setValue(self.current)

        for preset in [self.current, self.custom]:
            self.register_plug_preset(self["folderPath"], preset, preset)

        select_preset(self["folderPath"], self.current)

    def reload_product_types(self):
        folder_path_value = self.get_folder_path()

        if folder_path_value:

            product_types = get_product_types(
                self.get_project_name(),
                folder_path_value,
                self.type_filter)

            if product_types and not plug_presets_exists(
                self["productType"],
                product_types):

                selected = self["productType"].getValue()

                if product_types:
                    self.deregister_plug_presetes(self["productType"])

                for i, p_type in enumerate(product_types):

                    self.register_plug_preset(
                        self["productType"],
                        p_type,
                        p_type)

                    if selected == p_type:
                        select_preset(self["productType"], p_type)
                    elif i == 0:
                        select_preset(self["productType"], product_types[0])

    def reload_product_names(self):
        folder_path_value = self.get_folder_path()
        product_type_value = self["productType"].getValue()

        if folder_path_value and product_type_value:

            product_names = get_product_names(
                self.get_project_name(),
                self.get_folder_path(),
                product_type_value)

            if product_names and not plug_values_exists(
                self["productName"],
                [str(i) for i in product_names]):

                selected = self["productName"].getValue()

                self.deregister_plug_presetes(self["productName"])

                for i, product in enumerate(product_names):
                    self.register_plug_preset(
                        self["productName"],
                        product["name"],
                        str(product))

                    if (selected == str(product)) or (i == 0):
                        select_preset(self["productName"], product["name"])

    def reload_product_versions(self):

        def version_status(version):
            return f"{version['name']} ({version['status']})"

        product_name_value = self["productName"].getValue()

        if product_name_value:
            product_id = ast.literal_eval(product_name_value)["id"]
            versions = get_product_versions(
                self.get_project_name(),
                product_id)

            if versions and not plug_values_exists(
                    self["productVersion"],
                    [str(i) for i in versions]):

                selected = self["productVersion"].getValue()

                self.deregister_plug_presetes(self["productVersion"])

                preset_selected = False

                for version in versions:
                    preset = version_status(version)
                    self.register_plug_preset(
                        self["productVersion"], preset, str(version))

                    if selected == str(version):
                        select_preset(self["productVersion"], preset)
                        preset_selected = True

                if versions and not preset_selected:
                    select_preset(
                        self["productVersion"],
                        version_status(versions[-1]))

    def reload_representations(self):

        product_version_value = self["productVersion"].getValue()

        if product_version_value:
            version_id = ast.literal_eval(product_version_value)["id"]
            representations = get_representations(
                self.get_project_name(),
                version_id)

            if representations and not plug_values_exists(
                    self["representation"],
                    [str(i["files"][0]) for i in representations]):

                selected = self["representation"].getValue()

                self.deregister_plug_presetes(self["representation"])

                for i, repr in enumerate(representations):
                    self.register_plug_preset(
                        self["representation"],
                        repr["files"][0]["name"],
                        str(repr["files"][0]))

                    if (selected == str(repr["files"][0])) or (i == 0):
                        select_preset(self["representation"],
                                      repr["files"][0]["name"])

    def reload_project_roots(self):
        project_roots = get_project_roots(self.get_project_name())

        if project_roots and not plug_values_exists(
            self["projectRoot"],
            project_roots.values()):

            selected = self["projectRoot"].getValue()

            self.deregister_plug_presetes(self["projectRoot"])

            for i, (key, value) in enumerate(project_roots.items()):
                self.register_plug_preset(self["projectRoot"], key, value)

                if (selected == value) or (i == 0):
                    select_preset(self["projectRoot"], key)

    def reload_file_name(self):
        representation_value = self["representation"].getValue()

        if representation_value:
            path = ast.literal_eval(representation_value)["path"]
            start = path.find("{")
            end = path.find("}")

            if start != -1 and end != -1:
                root_value = self["projectRoot"].getValue()
                file_name_value = self["fileName"].getValue()
                file_name = path[:start] + root_value + path[end + 1:]

                if file_name != file_name_value:
                    self["fileName"].setValue(file_name)
                    self.file_name = file_name

IECore.registerRunTimeTyped(ProductReader, typeName="AyonProductReader")

Gaffer.Metadata.registerNode(
    ProductReader,
    "description", "Ayon Product Reader",
    "graphEditor:childrenViewable", True,
    "icon", GAFFER_HOST_DIR + "/icons/ayon-logo.png",
    "nodeGadget:color", imath.Color3f(0.4, 0.4, 0.4),
    "noduleLayout:customGadget:addButtonTop:visible", False,
    "noduleLayout:customGadget:addButtonBottom:visible", False,
    "noduleLayout:customGadget:addButtonLeft:visible", False,
    "noduleLayout:customGadget:addButtonRight:visible", False,
    plugs={
        "reloadAll": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget"],

         "projectName": [
            "nodule:type", "",
             "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadProjectName": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

         "folderPath": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

         "folderPathCustom": [
            "nodule:type", "",
            "label", "Custom"],

        "reloadFolderPath": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "reloadFolderPathCustom": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "productType": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadProductType": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "productName": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadProductName": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "productVersion": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadProductVersion": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "representation": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadRepresentation": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "projectRoot": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "reloadProjectRoot": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],

        "fileName": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.FileSystemPathPlugValueWidget"
            ],

        "refreshCount": [
            "nodule:type", "",
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True]
        }
    )

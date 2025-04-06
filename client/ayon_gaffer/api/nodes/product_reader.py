import ast
import platform
from pathlib import Path

import ayon_api
import ayon_api.exceptions

from ayon_core.lib import Logger
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

def get_project_names():
    return ayon_api.get_project_names()

def get_project_roots(project_name):
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

def get_product_types(project_name, folder_path):
    products = get_products(project_name, folder_path)
    product_types = list(set(
        product['productType'] for product in list(products)))

    if not product_types:
        log.error(f"Can't get product types at '{project_name}{folder_path}'")

    return product_types

def get_product_names(project_name, folder_path, product_type):
    products = get_products(project_name, folder_path)
    product_names = [i for i in products if
                    i['productType'] == product_type]

    if not product_names:
        log.error(f"Can't get product names at '{project_name}{folder_path}'")

    return product_names

def get_product_versions(project_name, product_id):
    versions = ayon_api.get_versions(project_name, product_ids=[product_id])

    if not versions:
        log.error(f"Can't get product versions for product id: '{product_id}'")

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

class ProductReader(Gaffer.Box):

    def __init__(self, name="ProductReader"):

        Gaffer.Box.__init__(self, name)

        self.current = "current"
        self.custom = "custom"
        self.type_filter =[]

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

        self.reload_all()

    def plug_set(self, plug):
        if(plug.getName() == "projectName" or
           plug.getName() == "reloadProjectName"):
            if self.reload_product_types():
                self.reload_product_names()
                self.reload_product_versions()
                self.reload_representations()
                self.reload_project_roots()
                self.reload_resolved_path()

        elif(plug.getName() == "folderPath" or
             plug.getName() == "reloadFolderPath"):
            if self.reload_product_types():
                self.reload_product_names()
                self.reload_product_versions()
                self.reload_representations()
                self.reload_project_roots()
                self.reload_resolved_path()

        elif(plug.getName() == "folderPathCustom" or
             plug.getName() == "reloadFolderPathCustom"):
            if self.reload_product_types():
                self.reload_product_names()
                self.reload_product_versions()
                self.reload_representations()
                self.reload_project_roots()
                self.reload_resolved_path()

        elif(plug.getName() == "productType" or
             plug.getName() == "reloadProductType"):
            self.reload_product_names()
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()

        elif(plug.getName() == "productName" or
             plug.getName() == "reloadProductName"):
            self.reload_product_versions()
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()

        elif(plug.getName() == "productVersion" or
             plug.getName() == "reloadProductVersion"):
            self.reload_representations()
            self.reload_project_roots()
            self.reload_resolved_path()

        elif(plug.getName() == "representation" or
             plug.getName() == "reloadRepresentation"):
            self.reload_project_roots()
            self.reload_resolved_path()

        elif(plug.getName() == "projectRoot" or
             plug.getName() == "reloadProjectRoot"):
            self.reload_resolved_path()

        elif(plug.getName() == "reloadAll"):
            self.reload_all()

    def register_plug_preset(self, plug, name, value):
        Gaffer.Metadata.registerPlugValue(plug, "preset:" + name, value)

    def deregister_plug_presetes(self, plug):
        metadata_keys = Gaffer.Metadata.registeredValues(plug)

        for key in metadata_keys:
            if key.startswith("preset:"):
                Gaffer.Metadata.deregisterValue(plug, key)

    def get_project_name(self):
        project_name = self["projectName"].getValue()

        if (project_name == self.current):
            return get_current_project_name()

        return project_name

    def get_folder_path(self):
        folder_path = self["folderPath"].getValue()

        if (folder_path == self.current):
            Gaffer.Metadata.registerValue(
                self["folderPathCustom"], "plugValueWidget:type", "")
            Gaffer.Metadata.registerValue(
                self["reloadFolderPathCustom"], "plugValueWidget:type", "")

            return get_current_folder_path()

        Gaffer.Metadata.registerValue(
                self["folderPathCustom"],
                "plugValueWidget:type",
                "GafferUI.StringPlugValueWidget")
        Gaffer.Metadata.registerValue(
                self["reloadFolderPathCustom"],
                "plugValueWidget:type",
                "GafferUI.RefreshPlugValueWidget")

        return self["folderPathCustom"].getValue()

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

        project_names = [self.current] + get_project_names()

        for name in project_names:
            self.register_plug_preset(self["projectName"], name, name)

        select_preset(self["projectName"], self.current)

    def reload_folder_path(self):
        self["folderPath"].setValue(self.current)

        for preset in [self.current, self.custom]:
            self.register_plug_preset(self["folderPath"], preset, preset)

        select_preset(self["folderPath"], self.current)

    def reload_product_types(self):
        product_types = get_product_types(
            self.get_project_name(),
            self.get_folder_path())

        if self.type_filter:
            product_types = [i for i in product_types if i in self.type_filter]

        if product_types:
            self.deregister_plug_presetes(self["productType"])

        for i, p_type in enumerate(product_types):

            self.register_plug_preset(
                self["productType"],
                p_type,
                p_type)

            if i == 0:
                select_preset(self["productType"], p_type)

        return product_types

    def reload_product_names(self):
        product_names = get_product_names(
            self.get_project_name(),
            self.get_folder_path(),
            self["productType"].getValue())

        if product_names:
            self.deregister_plug_presetes(self["productName"])

        for i, product in enumerate(product_names):
            self.register_plug_preset(
                self["productName"],
                product["name"],
                str(product))

            if i == 0:
                select_preset(self["productName"], product["name"])

    def reload_product_versions(self):
        product_name_value = self["productName"].getValue()

        if product_name_value:
            product_id = ast.literal_eval(product_name_value)["id"]
            versions = get_product_versions(self.get_project_name(), product_id)

            if versions:
                self.deregister_plug_presetes(self["productVersion"])

            picked_status = 0
            picked_version = {}

            for version in versions:
                self.register_plug_preset(
                    self["productVersion"],
                    f"{version['name']} ({version['status']})",
                    str(version))

                current_status = version_picker(version["status"])

                if picked_status >= current_status:
                    picked_status = current_status
                    picked_version = version

            if picked_version:
                select_preset(
                    self["productVersion"],
                    f"{picked_version['name']} ({picked_version['status']})")

    def reload_representations(self):
        product_version_value = self["productVersion"].getValue()

        if product_version_value:
            version_id = ast.literal_eval(product_version_value)["id"]
            representations = get_representations(
                self.get_project_name(),
                version_id)

            if representations:
                self.deregister_plug_presetes(self["representation"])

            for i, repr in enumerate(representations):
                self.register_plug_preset(
                    self["representation"],
                    repr["files"][0]["name"],
                    str(repr["files"][0]))

                if i == 0:
                    select_preset(self["representation"],
                                repr["files"][0]["name"])

    def reload_project_roots(self):
        project_roots = get_project_roots(self.get_project_name())

        if project_roots:
            self.deregister_plug_presetes(self["projectRoot"])

        for i, (key, value) in enumerate(project_roots.items()):
            self.register_plug_preset(self["projectRoot"], key, value)

            if i == 0:
                select_preset(self["projectRoot"], key)

    def reload_resolved_path(self):
        representation_value = self["representation"].getValue()

        if representation_value:
            path = ast.literal_eval(representation_value)["path"]

            start = path.find("{")
            end = path.find("}")

            if start != -1 and end != -1:
                root = self["projectRoot"].getValue()
                resolved_path = path[:start] + root + path[end + 1:]

                self["fileName"].setValue(resolved_path)

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

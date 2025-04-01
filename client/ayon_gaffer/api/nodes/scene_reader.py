import ast
import platform
from pathlib import Path

import ayon_api

from ayon_core.lib import Logger
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path)

import IECore
import Gaffer
import GafferScene


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
    folder = ayon_api.get_folder_by_path(project_name, folder_path)

    if folder is not None:
        folder_id = folder.get("id")
        products = ayon_api.get_products(project_name, folder_ids=[folder_id])

        return products
    else:
        log.error(
            f"Can't get any product at '{project_name}{folder_path}'")

    return []

def get_product_types(project_name, folder_path):
    products = get_products(project_name, folder_path)
    product_types = list(set(
        product['productType'] for product in list(products)))

    return product_types

def get_product_names(project_name, folder_path, product_type):
    products = get_products(project_name, folder_path)
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

class SceneReader(GafferScene.SceneNode):

    def __init__(self, name="SceneReader"):

        GafferScene.SceneNode.__init__(self, name)

        self.current = "current"

        self.addChild(Gaffer.IntPlug("reload",
                                     Gaffer.Plug.Direction.In))
        self.addChild(Gaffer.StringPlug("projectName",
                                        Gaffer.Plug.Direction.In,
                                        self.current))
        self.addChild(Gaffer.StringPlug("folderPath",
                                        Gaffer.Plug.Direction.In,
                                        self.current))
        self.addChild(Gaffer.StringPlug("folderPathCustom",
                                        Gaffer.Plug.Direction.In))
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

        if "sceneReader" not in self.keys():
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

    def get_project_name(self):
        project_name = self["projectName"].getValue()

        if (project_name == self.current):
            return get_current_project_name()

        return project_name

    def get_folder_path(self):
        folder_path = self["folderPath"].getValue()

        if (folder_path == self.current):
            Gaffer.Metadata.registerValue(
                self["folderPathCustom"],
                "plugValueWidget:type", "")

            return get_current_folder_path()

        Gaffer.Metadata.registerValue(
                self["folderPathCustom"],
                "plugValueWidget:type",
                "GafferUI.StringPlugValueWidget"
                "label", "Custom")

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
            self.register_plug_presetes(self["projectName"], name, name)

        select_preset(self["projectName"], self.current)

    def reload_folder_path(self):
        self["folderPath"].setValue(self.current)

        for preset in [self.current, "custom"]:
            self.register_plug_presetes(self["folderPath"], preset, preset)

        select_preset(self["folderPath"], self.current)

    def reload_product_types(self):
        product_types = get_product_types(
            self.get_project_name(),
            self.get_folder_path())

        if product_types:
            self.deregister_plug_presetes(self["productType"])

        for i, p_type in enumerate(product_types):

            self.register_plug_presetes(
                self["productType"],
                p_type,
                p_type)

            if i == 0:
                select_preset(self["productType"], p_type)

    def reload_product_names(self):
        product_names = get_product_names(
            self.get_project_name(),
            self.get_folder_path(),
            self["productType"].getValue())

        if product_names:
            self.deregister_plug_presetes(self["productName"])

        for i, product in enumerate(product_names):
            self.register_plug_presetes(
                self["productName"],
                product["name"],
                str(product))

            if i == 0:
                select_preset(self["productName"], product["name"])

    def reload_product_versions(self):
        product_id = ast.literal_eval(self["productName"].getValue())["id"]
        versions = get_product_versions(self.get_project_name(), product_id)

        if versions:
            self.deregister_plug_presetes(self["productVersion"])

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
        version_id = ast.literal_eval(self["productVersion"].getValue())["id"]
        representations = get_representations(
            self.get_project_name(),
            version_id)

        if representations:
            self.deregister_plug_presetes(self["representation"])

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

        project_roots = get_project_roots(self.get_project_name())

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

IECore.registerRunTimeTyped(SceneReader, typeName="AyonSceneReader")

Gaffer.Metadata.registerNode(
    SceneReader,
    "description", "Ayon Product Reader",
    "graphEditor:childrenViewable", True,
    "icon", GAFFER_HOST_DIR + "/icons/ayon-logo.png",
    plugs={
        "reload": [
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget"],

         "projectName": [
             "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

         "folderPath": [
             "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productType": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productName": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "productVersion": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "representation": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "projectRoot": [
            "plugValueWidget:type", "GafferUI.PresetsPlugValueWidget"],

        "refreshCount": [
            "plugValueWidget:type", "GafferUI.RefreshPlugValueWidget",
            "layout:label", "",
            "layout:accessory", True],
        }
    )

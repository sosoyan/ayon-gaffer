from .product_reader import ProductReader

import Gaffer
import GafferScene
import IECore


class SceneReader(ProductReader):

    def __init__(self, name="SceneReader"):

        ProductReader.__init__(self, name)

        self.addChild(GafferScene.ScenePlug("out", Gaffer.Plug.Direction.Out))
        self.addChild(Gaffer.TransformPlug("transform",
                                           Gaffer.Plug.Direction.In))

        if "SceneReader" not in self.keys():
            self["SceneReader"] = GafferScene.SceneReader()
            self["SceneReader"]["fileName"].setInput(self["fileName"])
            self["SceneReader"]['refreshCount'].setInput(self["refreshCount"])
            self["SceneReader"]["transform"].setInput(self["transform"])

        self["out"].setInput(self["SceneReader"]["out"])

        Gaffer.Metadata.registerValue(self["transform"],
                                      "layout:section",
                                      "Transform")


IECore.registerRunTimeTyped(SceneReader, typeName="AyonSceneReader")

Gaffer.Metadata.registerNode(
    SceneReader,
    "description", "Ayon Scene Reader",
    plugs={
        "transform": [
            "nodule:type", ""],
    }
)
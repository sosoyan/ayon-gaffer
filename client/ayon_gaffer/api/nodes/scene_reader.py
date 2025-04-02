from .product_reader import ProductReader

import Gaffer
import GafferScene
import IECore


class SceneReader(ProductReader):

    def __init__(self, name="SceneReader"):

        ProductReader.__init__(self, name)

        self.addChild(GafferScene.ScenePlug("out", Gaffer.Plug.Direction.Out))

        if "SceneReader" not in self.keys():
            self["SceneReader"] = GafferScene.SceneReader()
            self["SceneReader"]["fileName"].setInput(self["fileName"])
            self["SceneReader"]["refreshCount"].setInput(self["refreshCount"])

        self.promotePlug(self["SceneReader"]["transform"])

        Gaffer.Metadata.registerValue(
            self["transform"],
            "layout:section",
            "Transform")

        self["out"].setInput(self["SceneReader"]["out"])

IECore.registerRunTimeTyped(SceneReader, typeName="AyonSceneReader")

from .product_reader import ProductReader

import Gaffer
import GafferScene
import IECore


class SceneReader(ProductReader):

    def __init__(self, name="SceneReader"):

        ProductReader.__init__(self, name)

        self.addChild(Gaffer.TransformPlug("transform"))
        self.addChild(GafferScene.ScenePlug("out", Gaffer.Plug.Direction.Out))

        self["SceneReader"] = GafferScene.SceneReader()
        self["SceneReader"]["fileName"].setInput(self["fileName"])
        self["SceneReader"]["refreshCount"].setInput(self["refreshCount"])
        self["SceneReader"]["transform"].setInput(self["transform"])

        self["out"].setInput(self["SceneReader"]["out"])

IECore.registerRunTimeTyped(SceneReader, typeName="AyonSceneReader")

Gaffer.Metadata.registerNode(
    SceneReader,
    plugs={
        "transform": [
            "nodule:type", "",
            "layout:section", "Transform"]
    }
)

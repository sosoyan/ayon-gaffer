from .product_reader import ProductReader

import Gaffer
import GafferScene
import IECore


class SceneReader(ProductReader):

    def __init__(self, name="SceneReader"):

        ProductReader.__init__(self, name)

        self.addChild(Gaffer.TransformPlug("transform",
                                           Gaffer.Plug.Direction.In))

        if "sceneReader" not in self.keys():
            self["sceneReader"] = GafferScene.SceneReader()
            self["sceneReader"]["fileName"].setInput(self["filePath"])
            self["sceneReader"]['refreshCount'].setInput(self["refreshCount"])
            self["sceneReader"]["transform"].setInput(self["transform"])
            self["out"].setInput(self["sceneReader"]["out"])

        Gaffer.Metadata.registerValue(self["transform"],
                                      "layout:section",
                                      "Transform")


IECore.registerRunTimeTyped(SceneReader, typeName="AyonSceneReader")

from .product_reader import ProductReader

import Gaffer
import GafferImage
import IECore


class ImageReader(ProductReader):

    def __init__(self, name="ImageReader"):

        ProductReader.__init__(self, name)

        self.addChild(GafferImage.ImagePlug("out", Gaffer.Plug.Direction.Out))

        if "ImageReader" not in self.keys():
            self["ImageReader"] = GafferImage.ImageReader()
            self["ImageReader"]["fileName"].setInput(self["fileName"])
            self["ImageReader"]['refreshCount'].setInput(self["refreshCount"])

        self["out"].setInput(self["ImageReader"]["out"])

IECore.registerRunTimeTyped(ImageReader, typeName="AyonImageReader")

from .product_reader import ProductReader

import Gaffer
import GafferImage
import IECore


class ImageReader(ProductReader):

    def __init__(self, name="ImageReader"):

        ProductReader.__init__(self, name)

        self.addChild(GafferImage.ImagePlug("out", Gaffer.Plug.Direction.Out))

        self["ImageReader"] = GafferImage.ImageReader()
        self["ImageReader"]["fileName"].setInput(self["fileName"])
        self["ImageReader"]['refreshCount'].setInput(self["refreshCount"])

        self.promotePlug(self["ImageReader"]["missingFrameMode"])
        self.promotePlug(self["ImageReader"]["start"])
        self.promotePlug(self["ImageReader"]["end"])
        self.promotePlug(self["ImageReader"]["colorSpace"])
        self.promotePlug(self["ImageReader"]["channelInterpretation"])
        self.promotePlug(self["ImageReader"]["availableFrames"])
        self.promotePlug(self["ImageReader"]["fileValid"])

        for plug in self.children(Gaffer.Plug):
            plug.setFlags(Gaffer.Plug.Flags.Default)

        self["out"].setInput(self["ImageReader"]["out"])

IECore.registerRunTimeTyped(ImageReader, typeName="AyonImageReader")

Gaffer.Metadata.registerNode(
    ImageReader,
    plugs={
        "availableFrames": ["layout:section", "Frames"],
        "fileValid": ["layout:section", "Frames"]
    }
)
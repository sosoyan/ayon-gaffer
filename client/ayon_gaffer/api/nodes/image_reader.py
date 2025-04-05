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

    def reload_product_types(self):
        self.type_filter = ["image",
                            "render"]

        super().reload_product_types()

class ImageReaderSerialiser(Gaffer.NodeSerialiser):

    def childNeedsSerialisation(self, child, serialisation):

        if isinstance(child, Gaffer.Node):
            return False

        return Gaffer.NodeSerialiser.childNeedsSerialisation(
            self,
            child,
            serialisation)

IECore.registerRunTimeTyped(ImageReader, typeName="AyonImageReader")

Gaffer.Metadata.registerNode(
    ImageReader,
    plugs={
        "availableFrames": ["layout:section", "Frames"],
        "fileValid": ["layout:section", "Frames"]
    }
)

Gaffer.Serialisation.registerSerialiser(
    ProductReader,
    ImageReaderSerialiser()
)

import ast
from functools import partial

from PySide2 import QtCore

from ayon_core.lib import Logger
from .product_reader import ProductReader

import Gaffer
import IECore

log = Logger.get_logger(__name__)

class BoxReader(ProductReader):

    def __init__(self, name="BoxReader"):
        ProductReader.__init__(self, name)

        self.addChild(Gaffer.BoolPlug("loadAsReference",
                                      Gaffer.Plug.Direction.In,
                                      defaultValue=True))

    def plug_set(self, plug):
        super().plug_set(plug)

        if (plug.getName() == "fileName" or
            plug.getName() == "loadAsReference"):

            if self.scriptNode() is not None:
                self.reload_content()

        # Make sure the node is added to the graph before reloading
        elif (plug.getName() == "x" and
              self.scriptNode() is not None and
              not self.children(Gaffer.Node)):

                self.reload_content()

    def reload_product_types(self):
        self.type_filter = ["gafferNodes"]

        super().reload_product_types()

    def reload_content(self):
        input_plug = self.getChild("in")
        input_plug = input_plug.getInput() if input_plug else None

        output_plug = self.getChild("out")
        output_plug = output_plug.outputs() if output_plug else ()

        product_name_value = self["productName"].getValue()

        if product_name_value:

            for child in self.children(Gaffer.Node):
                self.removeChild(child)

            product_name = ast.literal_eval(product_name_value)["name"]

            if self["loadAsReference"].getValue():
                box = Gaffer.Reference(product_name)
                self.addChild(box)
                box.load(self["fileName"].getValue())
            else:
                box = Gaffer.Box(product_name)
                self.addChild(box)
                self.scriptNode().importFile(
                    self["fileName"].getValue(),
                    parent=box,
                    continueOnError=True)

            box_in = box.getChild("in")
            box_out = box.getChild("out")

            if box_in is not None:
                Gaffer.BoxIO.promote(box_in)

            if box_out is not None:
                Gaffer.BoxIO.promote(box_out)

            if box_in and box_out:
                self["BoxOut"]["passThrough"].setInput(
                    self["BoxIn"]["out"])

            if input_plug:
                box_in = self.getChild("in")
                if box_in:
                    box_in.setInput(input_plug)

            if output_plug:
                box_out = self.getChild("out")
                if box_out:
                    output_plug[0].setInput(box_out)


class BoxReaderSerialiser(Gaffer.NodeSerialiser):

    def childNeedsSerialisation(self, child, serialisation):

        if isinstance(child, Gaffer.Node):
            return True

        return Gaffer.NodeSerialiser.childNeedsSerialisation(
            self,
            child,
            serialisation)

IECore.registerRunTimeTyped(BoxReader, typeName="AyonBoxReader")

Gaffer.Serialisation.registerSerialiser(
    BoxReader,
    BoxReaderSerialiser()
)

Gaffer.Metadata.registerNode(
    BoxReader,
    plugs={
        "loadAsReference": ["nodule:type", ""]
    }
)
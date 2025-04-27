import ast

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

        self.parentChangedSignal().connect(self.parent_changed)

    def plug_set(self, plug):
        super().plug_set(plug)

        if (plug.getName() == "fileName" or
            plug.getName() == "loadAsReference"):

            script_node = plug.node().ancestor(Gaffer.ScriptNode)
            self.reload_content(script_node)

    def reload_product_types(self):
        self.type_filter = ["gafferNodes"]

        super().reload_product_types()

    def reload_content(self, script_node):

        if script_node is None:
            return

        input_plug = self.getChild("in")
        input_plug = input_plug.getInput() if input_plug else None

        output_plug = self.getChild("out")
        output_plug = output_plug.outputs() if output_plug else ()

        for child in self.children(Gaffer.Node):
                self.removeChild(child)

        product_name_value = self["productName"].getValue()
        product_name = ast.literal_eval(product_name_value)["name"]

        container = None

        if self["loadAsReference"].getValue():
            container = Gaffer.Reference(product_name)
            self.addChild(container)
            container.load(self["fileName"].getValue())
        else:
            container = Gaffer.Box(product_name)
            self.addChild(container)
            script_node.importFile(
                self["fileName"].getValue(),
                parent=container)

        ref_in = container.getChild("in")
        ref_out = container.getChild("out")

        if ref_in is not None:
            Gaffer.BoxIO.promote(ref_in)

        if ref_out is not None:
            Gaffer.BoxIO.promote(ref_out)

        if ref_in and ref_out:
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

    def parent_changed(self, node, _):
        script_node = node.ancestor(Gaffer.ScriptNode)
        self.reload_content(script_node)

class ReferenceReaderSerialiser(Gaffer.NodeSerialiser):

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
    ReferenceReaderSerialiser()
)

Gaffer.Metadata.registerNode(
    BoxReader,
    plugs={
        "loadAsReference": ["nodule:type", ""]
    }
)
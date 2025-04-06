from .product_reader import ProductReader

import Gaffer
import IECore


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

        load_reference = self.getChild("loadAsReference")

        if (script_node is None) or (load_reference is None):
            return

        input_plug = self.getChild("in")
        if input_plug:
            input_plug = input_plug.getInput()

        output_plug = self.getChild("out")
        if output_plug:
            output_plug = output_plug.outputs()

        for child in self.children(Gaffer.Node):
                self.removeChild(child)

        if load_reference.getValue():
            reference = Gaffer.Reference()

            self.addChild(reference)

            reference.load(self["fileName"].getValue())
            ref_in = reference.getChild("in")
            ref_out = reference.getChild("out")

            if ref_in is not None:
                Gaffer.BoxIO.promote(ref_in)

            if ref_out is not None:
                Gaffer.BoxIO.promote(ref_out)

            if ref_in and ref_out:
                self["BoxOut"]["passThrough"].setInput(
                    self["BoxIn"]["out"])
        else:
            script_node.importFile(
                self["fileName"].getValue(),
                parent=self)

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
from ayon_gaffer.api.nodes import product_reader

import GafferUI

def install_nodes(application):
    node_menu = GafferUI.NodeMenu.acquire(application)
    node_menu.append("/AYON/ProductReader",
                     lambda: product_reader.ProductReader(),
                     searchText="AyonProductReader")

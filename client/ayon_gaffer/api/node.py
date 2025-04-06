from ayon_gaffer.api.nodes import (ImageReader,
                                   SceneReader,
                                   BoxReader)

import GafferUI

def install_nodes(application):
    node_menu = GafferUI.NodeMenu.acquire(application)

    node_menu.append("/AYON/BoxReader",
                    BoxReader,
                    searchText="AyonBoxReader")

    node_menu.append("/AYON/ImageReader",
                     ImageReader,
                     searchText="AyonImageReader")

    node_menu.append("/AYON/SceneReader",
                     SceneReader,
                     searchText="AyonSceneReader")


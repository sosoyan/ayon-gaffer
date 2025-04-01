from ayon_gaffer.api.nodes import SceneReader

import GafferUI

def install_nodes(application):
    node_menu = GafferUI.NodeMenu.acquire(application)
    node_menu.append("/AYON/SceneReader",
                     SceneReader,
                     searchText="AyonSceneReader")

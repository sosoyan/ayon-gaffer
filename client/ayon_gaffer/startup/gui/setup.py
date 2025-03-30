from ayon_core.lib import Logger
from ayon_core.pipeline import install_host

from ayon_gaffer.api import GafferHost
from ayon_gaffer.api.menu import install_menu
from ayon_gaffer.api.node import install_nodes


log = Logger.get_logger(__name__)

application = application # noqa

def _install_ayon():
    """
    Installs the Ayon host and menu
    """
    log.info("Installing Ayon ...")
    install_host(GafferHost(application))
    install_menu(application)
    install_nodes(application)

_install_ayon()

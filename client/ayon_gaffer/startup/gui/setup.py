from ayon_core.lib import Logger
from ayon_core.pipeline import install_host

from ayon_gaffer.api import GafferHost
from ayon_gaffer.api.menu import install_menu


log = Logger.get_logger(__name__)

def _install_ayon():
    """
    Installs the Ayon application by setting up the Gaffer host and menu.

    This function logs the installation process, installs the Gaffer host for the
    given application, and sets up the application menu.

    Note:
        The `install_host` and `install_menu` functions are called with type ignore
        comments to bypass application being not defined issue.

    Returns:
        None
    """
    log.info("Installing Ayon ...")
    install_host(GafferHost(application)) # type: ignore
    install_menu(application) # type: ignore

_install_ayon()

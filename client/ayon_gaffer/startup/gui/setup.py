from ayon_core.lib import Logger
from ayon_core.pipeline import install_host

from ayon_gaffer.api import GafferHost
from ayon_gaffer.api.menu import install_menu
from ayon_gaffer.api.project import setup_project


log = Logger.get_logger("ayon_gaffer.startup.gui.setup")

application.root()["scripts"].childAddedSignal().connect(setup_project, scoped = False)

def _install_ayon():
    log.info("Installing ayon ...")
    install_host(GafferHost(application))
    install_menu(application)

_install_ayon()

import sys
from typing import NoReturn, Optional

import pyvisa
from PySide6.QtWidgets import QApplication

from src.controller.vrg_controller import VRGController
from src.model.vrg_driver import VRG
from src.view.main_window import MainWindow

"""
TODO: Make the QLineEdit text green
"""


def run_app() -> NoReturn:
    """
    *Set the version of application build, create the app by implementing the
    model-view-controller design pattern.
    *Execute the application event loop.
    *Note: `app.exec() == 0` when the event loop stops. `sys.exit(0)` terminates the application.
    """

    version = '1.0.0'
    app = QApplication([])

    model = VRG(resource_name='ASRL1::INSTR')
    view = MainWindow(version)
    controller = VRGController(model, view)  # noqa: F841

    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()

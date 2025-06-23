import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from helpers.helpers import get_ini_info
from src.controller.rf_controller import RFController
from src.model.vrg_driver import VRG
from src.view.main_window import MainWindow

"""
TODO:
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

    # Get the com port and rf settings from the ini file
    rf_com_port: str | None
    rf_settings: tuple[str, str, str]
    rf_com_port, rf_settings = get_ini_info()

    # Get the individual rf generator settings/specs
    min_freq: float = float(rf_settings[0])
    max_freq: float = float(rf_settings[1])
    max_power: int = int(rf_settings[2])

    # Set the frequency range
    freq_range: tuple[float, float] = (min_freq, max_freq)

    # Set up the model-view-controller design pattern
    model = VRG(resource_name=rf_com_port, freq_range=freq_range, max_power=max_power)
    view = MainWindow(version)
    controller = RFController(model, view)  # noqa: F841

    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()

from ..model.vrg_driver import VRG
from ..view.main_window import MainWindow


class VRGController:
    def __init__(self, model: VRG, view: MainWindow) -> None:
        self.model = model
        self.view = view

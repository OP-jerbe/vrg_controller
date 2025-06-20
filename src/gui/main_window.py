from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version

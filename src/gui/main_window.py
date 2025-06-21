from pathlib import Path

from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QLabel, QLineEdit, QMainWindow, QMenu, QMenuBar
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir


class MainWindow(QMainWindow):
    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version

        self.create_gui()

    def create_gui(self) -> None:
        window_width = 500
        window_height = 300
        self.setFixedSize(window_width, window_height)

        root_dir: Path = get_root_dir()
        print(str(root_dir))
        icon_path: str = str(root_dir / 'assets' / 'vrg_icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle('VRG Controller')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)

        self.create_menu_bar()

    def create_menu_bar(self) -> None:
        # Create the menu bar
        menu_bar = self.menuBar()

        # Create the menu bar items
        file_menu = menu_bar.addMenu('File')
        options_menu = menu_bar.addMenu('Options')

        # Create the Power Mode submenu that will go in the Options menu item
        power_mode_submenu = QMenu('Power Mode', self)

        # Create a QActionGroup for the power options
        power_mode_group = QActionGroup(self)
        power_mode_group.setExclusive(True)

        # Create the QActions
        exit_action = QAction(text='Exit', parent=self)
        self.absorbed_action = QAction('Absorbed', self, checkable=True, checked=True)
        self.forward_action = QAction('Forward', self, checkable=True)

        # Add the QActions to the QActionGroup. This ensures the absorbed and forward action exclusive.
        power_mode_group.addAction(self.absorbed_action)
        power_mode_group.addAction(self.forward_action)

        # Add actions to the menu bar options
        file_menu.addAction(exit_action)
        power_mode_submenu.addAction(self.absorbed_action)
        power_mode_submenu.addAction(self.forward_action)

        # Add the submenu to the Options menu
        options_menu.addMenu(power_mode_submenu)

        # Connect the QActions to slots when clicked
        exit_action.triggered.connect(self.handle_exit)
        self.absorbed_action.triggered.connect(self.handle_absorbed_action)
        self.forward_action.triggered.connect(self.handle_forward_action)

    def handle_exit(self) -> None:
        self.close()

    def handle_absorbed_action(self) -> None:
        """
        Handle what happens when absorbed mode is checked in the power mode option menu
        """
        print('Power mode changed to absorbed mode')

    def handle_forward_action(self) -> None:
        """
        Handle what happens when forward mode is checked in the power mode option menu
        """
        print('Power mode changed to forward mode.')

from pathlib import Path

from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QLabel, QLineEdit, QMainWindow, QMenu, QPushButton
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
        self.create_widgets()

    def create_widgets(self) -> None:
        # Create the QLabels
        self.abs_power_label = QLabel('Absorbed Power')
        self.fwd_power_label = QLabel('Forward Power')
        self.rfl_power_label = QLabel('Reflected Power')
        self.freq_label = QLabel('Frequency')

        # Create the QLineEdit entry boxes for power and frequency settings
        self.power_le = QLineEdit()
        self.freq_le = QLineEdit()

        # Create the RF enable/disable button
        self.enable_rf_btn = QPushButton('Enable RF')
        self.enable_rf_btn.setCheckable(True)
        self.enable_rf_btn.clicked.connect(self.handle_rf_enable_btn_clicked)

        # Create the autotune button
        self.autotune_btn = QPushButton('Autotune')
        self.autotune_btn.clicked.connect(self.handle_autotune_btn_clicked)

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
        self.absorbed_action.triggered.connect(self.handle_abs_mode_selected)
        self.forward_action.triggered.connect(self.handle_fwd_mode_selected)

    def handle_exit(self) -> None:
        """
        Handle what happens when the Exit option is selected from the menu
        """
        self.close()

    def handle_abs_mode_selected(self) -> None:
        """
        Handle what happens when absorbed mode is checked in the power mode option menu
        """
        print('Power mode changed to absorbed mode')

    def handle_fwd_mode_selected(self) -> None:
        """
        Handle what happens when forward mode is checked in the power mode option menu
        """
        print('Power mode changed to forward mode.')

    def handle_rf_enable_btn_clicked(self) -> None:
        """
        Handle what happens when the RF Enable button is clicked.
        """
        if self.enable_rf_btn.isChecked():
            print('RF disabled.')
        else:
            print('RF enabled.')

    def handle_autotune_btn_clicked(self) -> None:
        """
        Handle what happens when the Autotune button is clicked.
        """
        print('Autotuned.')

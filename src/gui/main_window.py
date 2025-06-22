from pathlib import Path

from PySide6.QtGui import QAction, QActionGroup, QIcon, Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from helpers.helpers import get_root_dir

from .widget_styles import display_label_style, line_edit_style, setting_label_style


class MainWindow(QMainWindow):
    def __init__(self, version: str) -> None:
        super().__init__()

        # Get the build version
        self.version = version

        # Create GUI
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.create_gui()

    ####################################################################################
    ##############################     Create UI     ###################################
    ####################################################################################

    def create_gui(self) -> None:
        self.set_window_size()
        self.set_title_bar()
        self.create_menu_ui()
        self.create_widgets()
        self.set_widget_styles()
        self.set_ui_layout()

    def set_window_size(self) -> None:
        window_width = 500
        window_height = 300
        self.setFixedSize(window_width, window_height)

    def set_title_bar(self) -> None:
        # Get the root directory to the icon
        root_dir: Path = get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'vrg_icon.ico')

        # Set the icon
        self.setWindowIcon(QIcon(icon_path))

        self.setWindowTitle(f'VRG Controller v{self.version}')

    def create_menu_ui(self) -> None:
        # Create the QMenuBar object
        menu_bar = self.menuBar()

        # Create the QMenu objects
        file_menu = menu_bar.addMenu('File')
        options_menu = menu_bar.addMenu('Options')

        # Create the Power Mode submenu that will go in the Options menu
        power_mode_submenu = QMenu('Power Mode', self)

        # Create a QActionGroup for the power mode options
        power_mode_group = QActionGroup(self)
        power_mode_group.setExclusive(True)

        # Create the QActions
        exit_action = QAction(text='Exit', parent=self)
        self.absorbed_action = QAction('Absorbed', self, checkable=True, checked=True)
        self.forward_action = QAction('Forward', self, checkable=True)

        # Add the absorbed and forward QActions to the QActionGroup.
        power_mode_group.addAction(self.absorbed_action)
        power_mode_group.addAction(self.forward_action)

        # Add actions to the QMenu objects.
        file_menu.addAction(exit_action)
        power_mode_submenu.addAction(self.absorbed_action)
        power_mode_submenu.addAction(self.forward_action)

        # Add the submenu to the Options menu.
        options_menu.addMenu(power_mode_submenu)

        # Connect the QActions to slots when clicked
        exit_action.triggered.connect(self.handle_exit)
        self.absorbed_action.triggered.connect(self.handle_abs_mode_selected)
        self.forward_action.triggered.connect(self.handle_fwd_mode_selected)

    def create_widgets(self) -> None:
        # Create the QLabels
        self.power_setting_label = QLabel('Power (W)')
        self.freq_setting_label = QLabel('Frequncy (MHz)')
        self.abs_power_label = QLabel('Absorbed Power')
        self.abs_power_display_label = QLabel('0 W')
        self.fwd_power_label = QLabel('Forward Power')
        self.fwd_power_display_label = QLabel('0 W')
        self.rfl_power_label = QLabel('Reflected Power')
        self.rfl_power_display_label = QLabel('0 W')
        self.freq_label = QLabel('Frequency')
        self.freq_display_label = QLabel('0 MHz')

        # Create the QLineEdit entry boxes for power and frequency settings
        self.power_le = QLineEdit(placeholderText='Input Power Setting')
        self.freq_le = QLineEdit(placeholderText='Input Frequency Setting')

        # Create the RF enable/disable button
        self.enable_rf_btn = QPushButton('Enable RF')
        self.enable_rf_btn.setCheckable(True)
        self.enable_rf_btn.clicked.connect(self.handle_rf_enable_btn_clicked)

        # Create the autotune button
        self.autotune_btn = QPushButton('Autotune')
        self.autotune_btn.clicked.connect(self.handle_autotune_btn_clicked)

    def set_widget_styles(self) -> None:
        # Set the power and frequency display styles
        self.power_setting_label.setStyleSheet(setting_label_style())
        self.freq_setting_label.setStyleSheet(setting_label_style())
        self.abs_power_display_label.setStyleSheet(display_label_style())
        self.fwd_power_display_label.setStyleSheet(display_label_style())
        self.rfl_power_display_label.setStyleSheet(display_label_style())
        self.freq_display_label.setStyleSheet(display_label_style())
        self.power_le.setStyleSheet(line_edit_style())
        self.freq_le.setStyleSheet(line_edit_style())

    def set_ui_layout(self) -> None:
        # Create the layouts
        main_layout = QVBoxLayout()
        top_layout = QGridLayout()
        bot_layout = QGridLayout()

        # Add widgets to layouts
        top_layout.addWidget(self.enable_rf_btn, 0, 0)
        top_layout.addWidget(
            self.freq_setting_label, 0, 1, alignment=Qt.AlignmentFlag.AlignCenter
        )
        top_layout.addWidget(
            self.power_setting_label, 0, 2, alignment=Qt.AlignmentFlag.AlignCenter
        )
        top_layout.addWidget(self.autotune_btn, 1, 0)
        top_layout.addWidget(self.freq_le, 1, 1)
        top_layout.addWidget(self.power_le, 1, 2)

        bot_layout.addWidget(self.fwd_power_label, 0, 0)
        bot_layout.addWidget(self.abs_power_label, 0, 1)
        bot_layout.addWidget(self.fwd_power_display_label, 1, 0)
        bot_layout.addWidget(self.abs_power_display_label, 1, 1)
        bot_layout.addWidget(self.rfl_power_label, 2, 0)
        bot_layout.addWidget(self.freq_label, 2, 1)
        bot_layout.addWidget(self.rfl_power_display_label, 3, 0)
        bot_layout.addWidget(self.freq_display_label, 3, 1)

        # Add layouts to main_layout
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bot_layout)

        # Set the main layout container
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    ####################################################################################
    ##############################     HANDLERS     ####################################
    ####################################################################################

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

from ..model.vrg_driver import VRG
from ..view.main_window import MainWindow


class RFController:
    def __init__(self, model: VRG, view: MainWindow) -> None:
        self.model = model
        self.view = view
        self.command_widgets = (
            self.view.power_le,
            self.view.freq_le,
            self.view.enable_rf_btn,
            self.view.autotune_btn,
        )
        self._connect_handlers()
        if not self.model.instrument:
            self._disable_gui()

    def _read_interlock_bit(self) -> int:
        try:
            _, _, interlock_bit_str = self.model.read_status_byte().split()
            interlock_bit: int = int(interlock_bit_str)
            return interlock_bit
        except Exception as e:
            print(f'Error: {e}')
            return -1

    def _disable_gui(self) -> None:
        for widget in self.command_widgets:
            widget.setEnabled(False)

    def _enable_gui(self) -> None:
        for widget in self.command_widgets:
            widget.setEnabled(True)

    def _connect_handlers(self) -> None:
        # Connect the QLineEdits to their handlers
        self.view.power_le.returnPressed.connect(self._handle_power_le_returnPressed)
        self.view.freq_le.returnPressed.connect(self._handle_freq_le_returnPressed)
        self.view.power_le.power_value_committed.connect(self._handle_power_le_changed)
        self.view.freq_le.freq_value_committed.connect(self._handle_freq_le_changed)

        # Connect the QPushButtons to their handlers
        self.view.enable_rf_btn.clicked.connect(self._handle_rf_enable_btn_clicked)
        self.view.autotune_btn.clicked.connect(self._handle_autotune_btn_clicked)

        # Connect the QActions (from the menu) to their handlers
        self.view.connect_action.triggered.connect(self._handle_connect_clicked)
        self.view.exit_action.triggered.connect(self._handle_exit)
        self.view.absorbed_action.triggered.connect(self._handle_abs_mode_selected)
        self.view.forward_action.triggered.connect(self._handle_fwd_mode_selected)

    def _handle_exit(self) -> None:
        """
        Handle what happens when the Exit option is selected from the menu
        """
        self.view.close()

    def _handle_connect_clicked(self) -> None:
        print('Connect clicked')
        # try to connect to VRG
        # if connection is successful, enable command widgets

    def _handle_abs_mode_selected(self) -> None:
        """
        Handle what happens when absorbed mode is checked in the power mode option menu
        """
        print('Absorbed Mode clicked.')
        try:
            self.model.set_abs_mode()
        except Exception as e:
            print(f'Error: {e}')

    def _handle_fwd_mode_selected(self) -> None:
        """
        Handle what happens when forward mode is checked in the power mode option menu
        """
        print('Forward Mode clicked.')
        try:
            self.model.set_fwd_mode()
        except Exception as e:
            print(f'Error: {e}')

    def _handle_rf_enable_btn_clicked(self) -> None:
        """
        Handle what happens when the RF Enable button is clicked.
        """
        print('RF Enable button clicked.')
        try:
            if self.view.enable_rf_btn.isChecked():
                self.model.enable_rf()
            else:
                self.model.disable_rf()
        except Exception as e:
            print(f'Error: {e}')

    def _handle_autotune_btn_clicked(self) -> None:
        """
        Handle what happens when the Autotune button is clicked.
        """
        print('Autotune Clicked.')
        try:
            self.model.autotune()
            # might need a half second pause here
            new_freq = self.model.read_freq_setting()
            self.view.freq_le.setText(new_freq)
        except Exception as e:
            print(f'Error: {e}')

    def _handle_power_le_returnPressed(self) -> None:
        self.view.power_le.clearFocus()

    def _handle_freq_le_returnPressed(self) -> None:
        self.view.freq_le.clearFocus()

    def _handle_power_le_changed(self, new_value: str) -> None:
        try:
            print(f'Power Requested: {new_value}')
            power = int(new_value)
            self.model.set_rf_power(power)
        except Exception as e:
            print(f'Error: {e}')

    def _handle_freq_le_changed(self, new_value: str) -> None:
        try:
            print(f'Frequency Requested: {new_value}')
            freq = float(new_value)
            self.model.set_freq(freq)
        except Exception as e:
            print(f'Error: {e}')

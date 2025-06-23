from pyvisa.resources import MessageBasedResource

from helpers.helpers import get_ini_info

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
        self._connect_events_to_handlers()

        # If there is not instrument connected, disable the gui
        if not self.model.instrument:
            self._disable_gui()

        try:
            self.model.set_abs_mode()
        except Exception as e:
            print(f'Error: {e}')

        # Get the interlock status and set the enable button accordingly
        self._check_interlock()

    ####################################################################################
    ###########################    STATE CHECKERS    ###############################@
    ####################################################################################

    def _read_interlock_bit(self) -> int:
        """
        Gets the interlock bit from the status byte.

        Returns: int\n
            `0` if interlock OK.
            `1` if interlock circuit is open.
            `-1` if an error occurs
        """
        try:
            _, _, interlock_bit_str = self.model.read_status_byte().split()
            interlock_bit: int = int(interlock_bit_str)
            return interlock_bit
        except Exception as e:
            print(f'Error: {e}')
            return -1

    def _check_interlock(self) -> None:
        """
        Enables or disables the Enable RF button based on the interlock status.
        """
        interlock_bit = self._read_interlock_bit()
        match interlock_bit:
            case 0:
                print('Interlock bit = 0 (OK)')
                self.view.enable_rf_btn.setEnabled(True)
                self.view.enable_rf_btn.setText('Enable RF')
            case 1:
                print('Interlock bit = 1 (interlocked)')
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
            case -1:
                print('Interlock bit = -1 (error)')
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('COM Error')

    ####################################################################################
    #########################    GUI ENABLER/DISABLER    ###############################
    ####################################################################################

    def _disable_gui(self) -> None:
        """
        Disable all widgets that send commands to the RF generator
        """
        for widget in self.command_widgets:
            widget.setEnabled(False)

    def _enable_gui(self) -> None:
        """
        Enable all widgets that send commands to the RF generator.
        """
        for widget in self.command_widgets:
            widget.setEnabled(True)

    ####################################################################################
    ###############################    HANDLERS    #####################################
    ####################################################################################

    def _connect_events_to_handlers(self) -> None:
        """
        Connects the events of the widgets to the handler methods. Events include
        returnPressed, mouse clicks and
        """
        # Connect the QLineEdit events to their handlers
        self.view.power_le.returnPressed.connect(self._handle_power_le_returnPressed)
        self.view.freq_le.returnPressed.connect(self._handle_freq_le_returnPressed)
        self.view.power_le.power_value_committed.connect(self._handle_power_le_changed)
        self.view.freq_le.freq_value_committed.connect(self._handle_freq_le_changed)

        # Connect the QPushButton events to their handlers
        self.view.enable_rf_btn.clicked.connect(self._handle_rf_enable_btn_clicked)
        self.view.autotune_btn.clicked.connect(self._handle_autotune_btn_clicked)

        # Connect the QAction events (from the menu) to their handlers
        self.view.connect_action.triggered.connect(self._handle_connect_clicked)
        self.view.exit_action.triggered.connect(self._handle_exit)
        self.view.absorbed_action.triggered.connect(self._handle_abs_mode_selected)
        self.view.forward_action.triggered.connect(self._handle_fwd_mode_selected)

    def _handle_exit(self) -> None:
        """
        Close the main window.
        """
        self.view.close()

    def _handle_connect_clicked(self) -> None:
        """
        Try to connect to the RF generator.
        """
        print('Connect clicked')
        # Get ini info
        com_port, rf_settings = get_ini_info()
        min_freq: float = float(rf_settings[0])
        max_freq: float = float(rf_settings[1])
        freq_range = (min_freq, max_freq)
        max_power = int(rf_settings[2])

        # Connect to the RF generator
        self.model = VRG(com_port, freq_range=freq_range, max_power=max_power)

        # try to connect to VRG
        # if connection is successful, enable command widgets

    def _handle_abs_mode_selected(self) -> None:
        """
        Set the power mode to Absorbed.
        """
        print('Absorbed Mode clicked.')
        try:
            self.model.set_abs_mode()
            self.view.absorbed_action.setChecked(True)
        except Exception as e:
            print(f'Error: {e}')

    def _handle_fwd_mode_selected(self) -> None:
        """
        Set the power mode to Forward
        """
        print('Forward Mode clicked.')
        try:
            self.model.set_fwd_mode()
        except Exception as e:
            print(f'Error: {e}')

    def _handle_rf_enable_btn_clicked(self) -> None:
        """
        Turn on the RF if clicked. Turn off the RF if unclicked.
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
        Send the wideband autotune command to the RF generator.
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
        """
        Clear the focus of the PowerLineEdit.
        """
        self.view.power_le.clearFocus()

    def _handle_freq_le_returnPressed(self) -> None:
        """
        Clear the focus of the FreqLineEdit
        """
        self.view.freq_le.clearFocus()

    def _handle_power_le_changed(self, new_value: str) -> None:
        """
        Set the RF power to the string emitted by the `power_value_committed` Signal.
        """
        try:
            print(f'Power Requested: {new_value}')
            power = int(new_value)
            self.model.set_rf_power(power)
        except Exception as e:
            print(f'Error: {e}')

    def _handle_freq_le_changed(self, new_value: str) -> None:
        """
        Set the frequency to the string emitted by the `freq_value_committed` Signal.
        """
        try:
            print(f'Frequency Requested: {new_value}')
            freq = float(new_value)
            self.model.set_freq(freq)
        except Exception as e:
            print(f'Error: {e}')

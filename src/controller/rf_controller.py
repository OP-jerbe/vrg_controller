from PySide6.QtCore import QCoreApplication, QObject, QThreadPool, QTimer, Signal, Slot
from serial import SerialException

from helpers.helpers import convert_num_to_bits, get_ini_info

from ..model.vrg_driver import VRG
from ..view.main_window import MainWindow
from .polling_worker import PollingWorker


class RFController(QObject):
    data_acquired = Signal(dict)

    def __init__(self, model: VRG, view: MainWindow) -> None:
        super().__init__()
        self.model = model
        self.view = view
        self.shutting_down = False  # flag
        self.polling_in_progress = False  # flag
        self.interactive_widgets = (
            self.view.power_le,
            self.view.freq_le,
            self.view.enable_rf_btn,
            self.view.autotune_btn,
        )
        self.threadpool = QThreadPool()
        self._create_polling_timer()

        self._connect_events_to_handlers()

        # If there is not an instrument connected, disable the gui and return
        if not self.model.serial_port:
            self._disable_gui()
            return

        self._init_control()

    ####################################################################################
    #############################    BACKGROUND THREAD    ##############################
    ####################################################################################

    def _create_polling_timer(self) -> None:
        self.polling_timer = QTimer(interval=1000)
        self.polling_timer.timeout.connect(self._poll_vrg)
        if self.model.serial_port is not None and self.model.serial_port.is_open:
            self.polling_timer.start()

    def _get_vrg_data(self) -> None:
        try:
            data: dict[str, int | float | None] = {
                'status_num': self.model.status_byte,
                'power_setting': self.model.power,
                'freq_setting': self.model.freq,
                'fwd_power': self.model.fwd_power,
                'rfl_power': self.model.rfl_power,
                'abs_power': self.model.abs_power,
            }
            self.data_acquired.emit(data)

        except SerialException as se:
            print(f'Error polling data: {se}')
            data = {
                'status_num': -1,
                'power_setting': None,
                'freq_setting': None,
                'fwd_power': None,
                'rfl_power': None,
                'abs_power': None,
            }
            self.data_acquired.emit(data)
            self.polling_timer.stop()

        except Exception as e:
            print(f'UNEXPECTED ERROR!!!: {e}')
            raise

        finally:
            self.polling_in_progress = False

    @Slot()
    def _poll_vrg(self) -> None:
        if self.polling_in_progress or self.shutting_down:
            return
        self.polling_in_progress = True
        worker = PollingWorker(self._get_vrg_data)
        self.threadpool.start(worker)

    @Slot(dict)
    def _handle_update_ui(self, data: dict[str, int | float | None]) -> None:
        """
        Called every second by Worker to update view with model data.
        """
        print(f'{data = }')
        status_num = data['status_num']
        power_setting = data['power_setting']
        freq_setting = data['freq_setting']
        fwd_power = data['fwd_power']
        rfl_power = data['rfl_power']
        abs_power = data['abs_power']

        # Check the status byte and set the state of the Enable RF button
        if isinstance(status_num, int) and isinstance(abs_power, int):
            self._set_enable_rf_btn_state(status_num, abs_power)

        # Set displays to nonsense and return if there was an error.
        if status_num == -1:
            self.view.abs_power_display_label.setText('W')
            self.view.fwd_power_display_label.setText('W')
            self.view.rfl_power_display_label.setText('W')
            self.view.freq_display_label.setText('MHz')
            self._disable_gui()
            return

        # Set the display values in the GUI if there's no error
        if not self.view.power_le.hasFocus():
            self.view.power_le.setText(f'{power_setting:.0f}')
        if not self.view.freq_le.hasFocus():
            self.view.freq_le.setText(f'{freq_setting:.2f}')
        self.view.abs_power_display_label.setText(f'{abs_power:.0f} W')
        self.view.fwd_power_display_label.setText(f'{fwd_power:.0f} W')
        self.view.rfl_power_display_label.setText(f'{rfl_power:.0f} W')
        self.view.freq_display_label.setText(f'{freq_setting:.2f} MHz')

    ####################################################################################
    #########################    GUI ENABLER/DISABLER    ###############################
    ####################################################################################

    def _init_control(self) -> None:
        """
        Initialzed the controller settings upon start up
        """
        try:
            self.model.disable_echo()  # send "DE" to VRG
            self.model.output_enabled = False  # send "DR" to VRG
            self.model.set_abs_mode()  # send "PM1" to VRG
        except Exception as e:
            print(f'    Unexpected Error initializing GUI display: {e}')

    def _disable_gui(self) -> None:
        """
        Disable all widgets that send commands to the RF generator
        """
        for widget in self.interactive_widgets:
            widget.setEnabled(False)

    def _enable_gui(self) -> None:
        """
        Enable all widgets that send commands to the RF generator.
        """
        for widget in self.interactive_widgets:
            widget.setEnabled(True)

    ####################################################################################
    ###############################    HANDLERS    #####################################
    ####################################################################################

    def _connect_events_to_handlers(self) -> None:
        """
        Connects the events of the widgets to the handler methods.
        """
        # Connect signals to slots
        self.data_acquired.connect(self._handle_update_ui)

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

    def _handle_connect_clicked(self) -> None:
        """
        Try to connect to the RF generator.
        """
        print('Connect clicked')
        # Get ini info
        rf_com_port: str | None = get_ini_info()[0]

        # Connect to the RF generator
        if rf_com_port is not None:
            self.model.serial_port = self.model.open_connection(rf_com_port)
        if self.model.serial_port:
            self.model.flush_input_buffer()
            self._init_control()
            self._enable_gui()
            self.polling_timer.start()

    def _handle_abs_mode_selected(self) -> None:
        """
        Set the power mode to Absorbed.
        """
        print('Absorbed Mode clicked.')
        try:
            self.model.set_abs_mode()
        except Exception as e:
            print(f'    Error setting absorbed mode: {e}')

    def _handle_fwd_mode_selected(self) -> None:
        """
        Set the power mode to Forward
        """
        print('Forward Mode clicked.')
        try:
            self.model.set_fwd_mode()
        except Exception as e:
            print(f'    Error setting forward mode: {e}')

    def _handle_rf_enable_btn_clicked(self) -> None:
        """
        Turn on the RF if clicked. Turn off the RF if unclicked.
        """
        print('RF Enable button clicked.')
        try:
            if self.view.enable_rf_btn.isChecked():
                self.model.output_enabled = True
                self.view.enable_rf_btn.setText('RF On')
            else:
                self.model.output_enabled = False
                self.view.enable_rf_btn.setText('RF Off')
        except Exception as e:
            print(f'    Error enabling/disabling RF: {e}')

    def _handle_autotune_btn_clicked(self) -> None:
        """
        Send the wideband autotune command to the RF generator.
        """
        print('Autotune Clicked.')
        try:
            self.model.autotune()
            freq: float | None = self.model.freq
            self.view.freq_le.setText(f'{freq:.2f}')
            self.view.freq_display_label.setText(f'{freq:.2f} MHz')
        except Exception as e:
            print(f'    Error Autotuning: {e}')

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
            self.model.power = power
        except Exception as e:
            print(f'    Error setting power: {e}')

    def _handle_freq_le_changed(self, new_value: str) -> None:
        """
        Set the frequency to the string emitted by the `freq_value_committed` Signal.
        """
        try:
            print(f'Frequency Requested: {new_value}')
            freq = float(new_value)
            self.model.freq = freq
        except Exception as e:
            print(f'    Error setting frequency: {e}')

    def _handle_exit(self) -> None:
        """
        Close the main window.
        """
        self.view.close()

    ####################################################################################
    ##############################   STATE CHECKERS    #################################
    ####################################################################################

    def _set_enable_rf_btn_state(self, status_num: int, abs_power: int | None) -> None:
        """
        Enables or disables the Enable RF button based on the interlock status.
        Matches the case of status bits.
        status_num[0] == not currently used - (Always 0)
        status_num[1] == Enable Switch OFF / ON - (0 / 1)
        status_num[2] == Temp OK / Over Temp -  (0 / 1)
        status_num[3] == Not Interlocked / Interlocked - (0 / 1)
        """
        if status_num == -1:  # error occured
            print('status_num = -1 (error)')
            self.view.enable_rf_btn.setChecked(False)
            self.view.enable_rf_btn.setEnabled(False)
            self.view.enable_rf_btn.setText('COM Error')

        status_bits: list[int] = convert_num_to_bits(status_num)

        match status_bits:
            case [0, 0, 0, 0]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('RF Off')
                self.view.enable_rf_btn.setEnabled(True)
            case [0, 0, 0, 1]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('INT')
                self.view.enable_rf_btn.setEnabled(False)
            case [0, 0, 1, 0]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(True)
                self.view.enable_rf_btn.setText('High Temp')
            case [0, 0, 1, 1]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
            case [0, 1, 0, 0]:
                self.view.enable_rf_btn.setEnabled(True)
                if abs_power is not None and abs_power > 0:
                    self.view.enable_rf_btn.setChecked(True)
                    self.view.enable_rf_btn.setText('RF On')
            case [0, 1, 0, 1]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('INT')
                self.view.enable_rf_btn.setEnabled(False)
            case [0, 1, 1, 0]:
                self.view.enable_rf_btn.setText('High Temp')
            case [0, 1, 1, 1]:
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
            case _:
                print(f'Unexpected status_bit list:  {status_bits}')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('Unk Error')
                self.view.enable_rf_btn.setEnabled(False)

    def shutdown(self) -> None:
        self.shutting_down = True
        self.polling_timer.stop()
        QCoreApplication.processEvents()

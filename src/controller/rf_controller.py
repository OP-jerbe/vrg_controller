from PySide6.QtCore import QCoreApplication, QThread

from helpers.helpers import get_ini_info

from ..model.vrg_driver import VRG
from ..view.main_window import MainWindow
from .bg_thread import Worker


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

        # Create the backgroud thread and worker to update GUI with readback values
        self._create_bg_thread()

        # If there is not an instrument connected, disable the gui and return
        if not self.model.instrument:
            self._disable_gui()
            return

        self._init_control()

        # Start the background thread updates
        self.worker_thread.start()

    ####################################################################################
    #############################    BACKGROUND THREAD    ##############################
    ####################################################################################

    def _create_bg_thread(self) -> None:
        """
        Create the background Qthread and Worker objects. Move the Worker to the
        background thread and connect Signals to their handler methods.
        """
        self.worker_thread = QThread()
        self.worker = Worker(self.model)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.start)
        self.worker.updated.connect(self._handle_update_ui)
        self.worker.stopped.connect(self._on_worker_stopped)

    def _on_worker_stopped(self) -> None:
        self.stop_bg_thread()

    def stop_bg_thread(self) -> None:
        # Emit signal to request worker to stop
        self.worker.stop_requested.emit()

        # Give control back to event loop so that stop() runs in the worker thread
        QCoreApplication.processEvents()

        # Stop the thread
        self.worker_thread.quit()
        self.worker_thread.wait()  # Blocks until thread exits

    def _handle_update_ui(self, data: dict[str, int | float | None]) -> None:
        """
        Called every second by Worker to update view with model data.
        """
        interlock_bit = data['interlock_bit']
        power_setting = data['power_setting']
        freq_setting = data['freq_setting']
        fwd_power = data['fwd_power']
        rfl_power = data['rfl_power']
        abs_power = data['abs_power']

        # Check the interlock bit and set the state of the Enable RF button
        if isinstance(interlock_bit, int) and not isinstance(abs_power, float):
            self._set_enable_rf_btn_state(interlock_bit, abs_power)

        # Set displays to nonsense and return if there was an error.
        if interlock_bit == -1:
            self.view.abs_power_display_label.setText('### W')
            self.view.fwd_power_display_label.setText('### W')
            self.view.rfl_power_display_label.setText('### W')
            self.view.freq_display_label.setText('### MHz')
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
            self.model.disable_rf()  # send "DR" to VRG
            self.model.set_abs_mode()  # send "PM1" to VRG
        except TypeError as te:
            print(f'    TypeError: {te}')
        except Exception as e:
            print(f'    Unexpected Error initializing GUI display: {e}')

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

    def _handle_connect_clicked(self) -> None:
        """
        Try to connect to the RF generator.
        """
        print('Connect clicked')
        # Get ini info
        rf_com_port: str | None
        rf_settings: tuple[str, str, str]
        rf_com_port, rf_settings = get_ini_info()

        resource_name = rf_com_port
        if rf_com_port is not None:
            resource_name = f'ASRL{rf_com_port[-1]}::INSTR'
        min_freq = float(rf_settings[0])
        max_freq = float(rf_settings[1])
        freq_range = (min_freq, max_freq)
        max_power = int(rf_settings[2])

        # Connect to the RF generator
        try:
            self.model = VRG(resource_name, freq_range=freq_range, max_power=max_power)
            self._init_control()
            self.view.autotune_btn.setEnabled(True)
            self.model.flush_input_buffer()
            self.worker_thread.start()
        except Exception as e:
            print(f'    Error trying to connect to RF generator: {e}')

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
                self.model.enable_rf()
                self.view.enable_rf_btn.setText('RF On')
            else:
                self.model.disable_rf()
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
            freq: float | None = self.model.read_freq_setting()
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
            self.model.set_rf_power(power)
        except Exception as e:
            print(f'    Error setting power: {e}')

    def _handle_freq_le_changed(self, new_value: str) -> None:
        """
        Set the frequency to the string emitted by the `freq_value_committed` Signal.
        """
        try:
            print(f'Frequency Requested: {new_value}')
            freq = float(new_value)
            self.model.set_freq(freq)
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

    def _set_enable_rf_btn_state(
        self, interlock_bit: int, abs_power: int | None
    ) -> int:
        """
        Enables or disables the Enable RF button based on the interlock status.
        """
        match interlock_bit:
            case -1:
                print('    Interlock bit = -1 (error)')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('COM Error')
                return interlock_bit
            case 0:
                print('    Interlock bit = 0 (OK - Enable Switch OFF)')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('RF Off')
                self.view.enable_rf_btn.setEnabled(True)
                return interlock_bit
            case 1:
                print('    Interlock bit = 1 (interlocked - Enable Switch OFF)')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
                return interlock_bit
            case 2:
                print('    Interlock bit = 2 (HiT Warning - Enable Switch OFF)')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(True)
                self.view.enable_rf_btn.setText('High Temp')
                return interlock_bit
            case 3:
                print(
                    '    Interlock bit = 3 (HiT Warning and interlocked - Enable Switch OFF)'
                )
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
                return interlock_bit
            case 4:
                print('    Interlock bit = 4 (OK - Enable Switch ON)')
                self.view.enable_rf_btn.setEnabled(True)
                if abs_power is not None and abs_power > 0:
                    self.view.enable_rf_btn.setChecked(True)
                    self.view.enable_rf_btn.setText('RF On')
                return interlock_bit
            case 5:
                print('    Interlock bit = 5 (interlocked - Enable Switch ON)')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('INT')
                self.view.enable_rf_btn.setEnabled(False)
                return interlock_bit
            case 6:
                print('    Interlock bit = 6 (HiT Warning - Enable Switch ON)')
                self.view.enable_rf_btn.setText('High Temp')
                return interlock_bit
            case 7:
                print(
                    '    Interlock bit = 7 (HiT Warning and interlocked - Enable Switch ON)'
                )
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setEnabled(False)
                self.view.enable_rf_btn.setText('INT')
                return interlock_bit
            case _:
                print(f'    Unexpected bit:  {interlock_bit}')
                self.view.enable_rf_btn.setChecked(False)
                self.view.enable_rf_btn.setText('Unk Error')
                self.view.enable_rf_btn.setEnabled(False)
                return interlock_bit

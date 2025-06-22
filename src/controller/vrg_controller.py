from ..model.vrg_driver import VRG
from ..view.main_window import MainWindow


class VRGController:
    def __init__(self, model: VRG, view: MainWindow) -> None:
        self.model = model
        self.view = view
        self._connect_handlers()

    def _connect_handlers(self) -> None:
        # Connect the QLineEdits to their handlers
        self.view.power_le.returnPressed.connect(self._handle_power_le_returnPressed)
        self.view.freq_le.returnPressed.connect(self._handle_freq_le_returnPressed)

        # Connect the QPushButtons to their handlers
        self.view.enable_rf_btn.clicked.connect(self._handle_rf_enable_btn_clicked)
        self.view.autotune_btn.clicked.connect(self._handle_autotune_btn_clicked)

        # Connect the QActions (from the menu) to their handlers
        self.view.exit_action.triggered.connect(self._handle_exit)
        self.view.absorbed_action.triggered.connect(self._handle_abs_mode_selected)
        self.view.forward_action.triggered.connect(self._handle_fwd_mode_selected)

    def _handle_exit(self) -> None:
        """
        Handle what happens when the Exit option is selected from the menu
        """
        self.view.close()

    def _handle_abs_mode_selected(self) -> None:
        """
        Handle what happens when absorbed mode is checked in the power mode option menu
        """
        print('Power mode changed to absorbed mode')
        if not self.model.instrument:
            return
        self.model.set_abs_mode()

    def _handle_fwd_mode_selected(self) -> None:
        """
        Handle what happens when forward mode is checked in the power mode option menu
        """
        print('Power mode changed to forward mode.')
        if not self.model.instrument:
            return
        self.model.set_fwd_mode()

    def _handle_rf_enable_btn_clicked(self) -> None:
        """
        Handle what happens when the RF Enable button is clicked.
        """
        if self.view.enable_rf_btn.isChecked():
            print('RF enabled.')
            if not self.model.instrument:
                return
            self.model.enable_rf()
        else:
            print('RF disabled.')
            if not self.model.instrument:
                return
            self.model.disable_rf()

    def _handle_autotune_btn_clicked(self) -> None:
        """
        Handle what happens when the Autotune button is clicked.
        """
        print('Autotuned.')
        if not self.model.instrument:
            return
        self.model.autotune()

    def _handle_power_le_returnPressed(self) -> None:
        text = self.view.power_le.text()
        print(text)
        self.view.power_le.clearFocus()
        # send set_power command

    def _handle_freq_le_returnPressed(self) -> None:
        text = self.view.freq_le.text()
        print(text)
        self.view.freq_le.clearFocus()
        # send set_freq command

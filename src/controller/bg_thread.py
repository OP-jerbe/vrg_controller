import traceback

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from ..model.vrg_driver import VRG


class Worker(QObject):
    """
    Creates a Worker object to signal to the controller to update the view once per second.
    """

    updated = Signal(dict)
    stop_requested = Signal()
    stopped = Signal()

    def __init__(self, model: VRG) -> None:
        super().__init__()
        self.model = model
        self.timer = None
        self.stop_requested.connect(self.stop, Qt.ConnectionType.QueuedConnection)

    def start(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start()

    def stop(self) -> None:
        if self.timer and self.timer.isActive():
            self.timer.stop()
        self.stopped.emit()

    def on_timeout(self) -> None:
        try:
            data: dict[str, int | float | None] = {
                'interlock_bit': self.model.read_status_byte()[-1],
                'power_setting': self.model.read_power_setting(),
                'freq_setting': self.model.read_freq_setting(),
                'fwd_power': self.model.read_fwd_power(),
                'rfl_power': self.model.read_rfl_power(),
                'abs_power': self.model.read_abs_power(),
            }
        except Exception as e:
            print(f'    Error polling data: {e}')
            print(f'    Traceback :{traceback.print_exc()}')
            data = {
                'interlock_bit': -1,
                'power_setting': None,
                'freq_setting': None,
                'fwd_power': None,
                'rfl_power': None,
                'abs_power': None,
            }
        self.updated.emit(data)

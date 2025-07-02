from PySide6.QtCore import QObject, Qt, QTimer, Signal
from serial import SerialException

from ..model.vrg_driver import VRG


class Worker(QObject):
    """
    Creates a Worker object to signal to the controller to update the view once per second.
    """

    updated = Signal(dict)
    disconnected = Signal()
    stop_requested = Signal()
    stopped = Signal()

    def __init__(self, model: VRG) -> None:
        super().__init__()
        self.model = model
        self.timer = None
        self.stop_requested.connect(self.stop, Qt.ConnectionType.QueuedConnection)
        self.disconnected.connect(self.stop, Qt.ConnectionType.QueuedConnection)

    def start(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start()

    def stop(self) -> None:
        if self.timer:
            if self.timer.isActive():
                self.timer.stop()
                print('QTimer Stopped...')
            self.timer.deleteLater()
            self.timer = None
        print('Worker is stopping...')
        self.stopped.emit()

    def on_timeout(self) -> None:
        try:
            data: dict[str, int | float | None] = {
                'status_num': self.model.read_status_byte(),
                'power_setting': self.model.read_power_setting(),
                'freq_setting': self.model.read_freq_setting(),
                'fwd_power': self.model.read_fwd_power(),
                'rfl_power': self.model.read_rfl_power(),
                'abs_power': self.model.read_abs_power(),
            }
            self.updated.emit(data)
        except SerialException as se:
            print(f'    Error polling data: {se}')
            data = {
                'status_num': -1,
                'power_setting': None,
                'freq_setting': None,
                'fwd_power': None,
                'rfl_power': None,
                'abs_power': None,
            }
            self.disconnected.emit()
        except Exception as e:
            print(f'UNEXPECTED ERROR!!!: {e}')
            raise

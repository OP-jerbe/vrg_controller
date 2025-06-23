from PySide6.QtCore import QObject, Qt, QTimer, Signal


class Worker(QObject):
    """
    Creates a Worker object to signal to the controller to update the view once per second.
    """

    updated = Signal()
    stop_requested = Signal()
    stopped = Signal()

    def __init__(self) -> None:
        super().__init__()
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
        self.updated.emit()

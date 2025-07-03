from PySide6.QtCore import QRunnable, Slot


class PollingWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self) -> None:
        self.fn(*self.args, **self.kwargs)

from collections.abc import Callable

from PyQt6.QtCore import QObject, QThread, QThreadPool, QTimer, pyqtSignal


class TaskRegistry(QObject):
    """主线程登记执行器，保留引用直到原生线程和线程池确实退出。"""

    idle = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.closing = False
        self._threads: dict[QThread, Callable[[], None]] = {}
        self._pools: dict[QThreadPool, set[Callable[[], None]]] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._reap)

    def add_thread(self, thread: QThread, cancel: Callable[[], None]) -> bool:
        if self.closing:
            cancel()
            return False
        self._threads[thread] = cancel
        self._timer.start()
        return True

    def add_pool(self, pool: QThreadPool, cancel: Callable[[], None]) -> bool:
        if self.closing:
            cancel()
            return False
        self._pools.setdefault(pool, set()).add(cancel)
        self._timer.start()
        return True

    def has_active(self) -> bool:
        self._reap()
        return bool(self._threads or self._pools)

    def begin_shutdown(self) -> None:
        if self.closing:
            return
        self.closing = True
        for cancel in list(self._threads.values()):
            cancel()
        for callbacks in list(self._pools.values()):
            for cancel in list(callbacks):
                cancel()
        self._reap()

    def _reap(self) -> None:
        had_tasks = bool(self._threads or self._pools)
        for thread in list(self._threads):
            if thread.wait(0):
                del self._threads[thread]
        for pool in list(self._pools):
            if pool.waitForDone(0):
                del self._pools[pool]
        if not self._threads and not self._pools:
            self._timer.stop()
            if had_tasks:
                self.idle.emit()


registry = TaskRegistry()


class ManagedThread(QThread):
    def start(self, priority=QThread.Priority.InheritPriority):
        if registry.add_thread(self, self.cancel):
            super().start(priority)

    def cancel(self):
        self.requestInterruption()

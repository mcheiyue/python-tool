from threading import Event
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QThreadPool, QTimer

from ui.main_window import MainWindow
from ui.threads import PoolTask, WorkerThread


@pytest.fixture(autouse=True)
def isolated_registry(qapp, monkeypatch):
    from core import task_registry

    registry = task_registry.TaskRegistry()
    monkeypatch.setattr(task_registry, "registry", registry)
    yield registry
    assert not registry.has_active()
    registry.deleteLater()


def test_cancelled_worker_reports_one_terminal_event_after_work_stops(qtbot):
    entered, release = Event(), Event()
    outcomes = []

    def work():
        entered.set()
        release.wait(15)
        return "done"

    worker = WorkerThread(work)
    worker.finished.connect(lambda result: outcomes.append("finished"))
    worker.error.connect(lambda message: outcomes.append("error"))
    worker.cancelled.connect(lambda: outcomes.append("cancelled"))
    worker.start()
    try:
        qtbot.waitUntil(entered.is_set)
        worker.cancel()
        assert outcomes == []
        release.set()
        qtbot.waitUntil(lambda: bool(outcomes))
        assert outcomes == ["cancelled"]
    finally:
        release.set()
        assert worker.wait(2000)


def test_cancel_after_success_is_reported_as_success(qtbot):
    written = Event()
    release = Event()
    outcomes = []

    def work():
        written.set()
        release.wait(15)
        return (True, "published")

    worker = WorkerThread(work)
    worker.finished.connect(lambda result: outcomes.append(result))
    worker.cancelled.connect(lambda: outcomes.append("cancelled"))
    worker.start()
    try:
        qtbot.waitUntil(written.is_set)
        release.set()
        assert worker.wait(2000)
        worker.cancel()
        qtbot.waitUntil(lambda: bool(outcomes))
        assert outcomes == [(True, "published")]
    finally:
        release.set()
        assert worker.wait(2000)


def test_cancel_before_start_does_not_run_task_and_reports_cancelled(qtbot):
    calls, outcomes = [], []
    worker = WorkerThread(lambda: calls.append("ran"))
    worker.cancelled.connect(lambda: outcomes.append("cancelled"))
    worker.cancel()

    worker.start()
    try:
        qtbot.waitUntil(lambda: bool(outcomes))
        assert outcomes == ["cancelled"]
        assert calls == []
    finally:
        assert worker.wait(2000)


@pytest.mark.parametrize("executor", ["worker", "pool", "resolver", "installer"])
def test_close_remains_responsive_until_background_work_really_finishes(qtbot, executor):
    entered, release = Event(), Event()
    ticks = []
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    timer = QTimer(window)
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(True))
    pool = QThreadPool()

    def work():
        entered.set()
        release.wait(20)

    if executor == "worker":
        worker = WorkerThread(work)
        worker.start()
    elif executor == "pool":
        task = PoolTask(work, (), {}, on_error=lambda message: None)
        task.start(pool)
    else:
        from core.external_tools.base import _StatusResolver, _ToolInstallWorker

        tool = SimpleNamespace(
            name="fake", display_name="测试工具", executable_names=("fake.exe",),
            portable_subdirs=("",), get_status_info=work,
            _install_from_package=lambda *args, **kwargs: work(),
        )
        worker = _StatusResolver(tool) if executor == "resolver" else _ToolInstallWorker(tool)
        worker.start()
    try:
        qtbot.waitUntil(entered.is_set)
        timer.start()
        window.close()
        assert window.isVisible(), "后台任务未结束时不能关闭窗口"
        qtbot.waitUntil(lambda: len(ticks) >= 2)
        window.close()
        assert window.isVisible(), "重复关闭也不能绕过等待"
        release.set()
        qtbot.waitUntil(lambda: not window.isVisible())
    finally:
        release.set()
        if executor != "pool":
            assert worker.wait(2000)
        assert pool.waitForDone(2000)
        window.close()


def test_shutdown_skips_queued_pool_work_and_rejects_new_threads(qtbot, isolated_registry, tmp_path):
    entered, release = Event(), Event()
    pool = QThreadPool()
    pool.setMaxThreadCount(1)
    output = tmp_path / "queued-output.txt"
    late_calls = []

    def first():
        entered.set()
        release.wait(10)

    first_task = PoolTask(first, (), {}, on_error=lambda message: None)
    next_task = PoolTask(lambda: output.write_text("unexpected"), (), {}, on_error=lambda message: None)
    first_task.start(pool)
    next_task.start(pool)
    try:
        qtbot.waitUntil(entered.is_set)
        isolated_registry.begin_shutdown()
        late_worker = WorkerThread(lambda: late_calls.append(True))
        late_worker.start()
        assert not late_worker.isRunning()
        assert isolated_registry.has_active()
        release.set()
        qtbot.waitUntil(lambda: not isolated_registry.has_active())
        assert not output.exists()
        assert late_calls == []
    finally:
        release.set()
        assert pool.waitForDone(2000)

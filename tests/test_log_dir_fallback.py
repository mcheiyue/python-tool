import pathlib

from core.utils import resource_path


def _deny_writes_under(monkeypatch, blocked: pathlib.Path):
    real_mkdir = pathlib.Path.mkdir

    def deny(self, *args, **kwargs):
        if str(self).startswith(str(blocked)):
            raise PermissionError(13, "denied", str(self))
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "mkdir", deny)


def test_data_root_falls_back_when_app_dir_unwritable(monkeypatch, tmp_path):
    """装到 Program Files 时程序目录只读，可写状态必须落到用户数据目录而不是崩掉。"""
    fake_app = tmp_path / "ProgramFilesApp"
    fake_app.mkdir()
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    _deny_writes_under(monkeypatch, fake_app)

    data_root = resource_path.get_data_root()
    log_dir = resource_path.get_log_dir()

    assert data_root == local_appdata / "OfficeToolkit"
    assert log_dir == data_root / "logs"
    assert log_dir.is_dir()


def test_data_root_falls_back_when_dir_exists_but_unwritable(monkeypatch, tmp_path):
    """目录已存在但不可写时必须回退：mkdir(exist_ok=True) 对已存在目录是空操作，
    只靠 mkdir 判断会把只读目录误判为可写，随后写日志才崩。"""
    fake_app = tmp_path / "ExistingApp"
    (fake_app / "logs").mkdir(parents=True)
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    real_write = pathlib.Path.write_bytes

    def deny(self, data):
        if str(self).startswith(str(fake_app)):
            raise PermissionError(13, "denied", str(self))
        return real_write(self, data)

    monkeypatch.setattr(pathlib.Path, "write_bytes", deny)

    assert resource_path.get_data_root() == local_appdata / "OfficeToolkit"


def test_log_dir_falls_back_when_logs_dir_exists_but_unwritable(monkeypatch, tmp_path):
    """程序目录里的 logs 已存在但不可写时，日志目录要换到用户数据目录。"""
    fake_app = tmp_path / "ExistingApp"
    (fake_app / "logs").mkdir(parents=True)
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    real_write = pathlib.Path.write_bytes

    def deny(self, data):
        if str(self).startswith(str(fake_app)):
            raise PermissionError(13, "denied", str(self))
        return real_write(self, data)

    monkeypatch.setattr(pathlib.Path, "write_bytes", deny)

    assert resource_path.get_log_dir() == local_appdata / "OfficeToolkit" / "logs"


def test_logger_degrades_instead_of_crashing_when_log_file_unwritable(monkeypatch, tmp_path):
    """日志文件打不开时只能降级，不能让进程在启动阶段就死掉。"""
    import logging

    from core.utils import logger as logger_module

    monkeypatch.setattr(logger_module, "get_log_dir", lambda: tmp_path / "logs")

    def deny(*args, **kwargs):
        raise PermissionError(13, "denied", str(tmp_path / "logs"))

    monkeypatch.setattr(logging, "FileHandler", deny)
    monkeypatch.setattr(logger_module.AppLogger, "_instance", None)
    try:
        logger_module.AppLogger()
    finally:
        logger_module.AppLogger._instance = None


def test_crash_handler_survives_unwritable_log_file(monkeypatch, tmp_path):
    """崩溃处理器的日志文件打不开时也不能抛异常，否则连崩溃弹窗都出不来。"""
    import logging

    from core.utils import crash_handler as crash_module

    monkeypatch.setattr(crash_module, "get_log_dir", lambda: tmp_path / "logs")

    def deny(*args, **kwargs):
        if args or kwargs.get("filename"):
            raise PermissionError(13, "denied", str(kwargs.get("filename")))

    monkeypatch.setattr(logging, "basicConfig", deny)

    crash_module.CrashHandler()


def test_data_root_stays_next_to_app_when_writable(monkeypatch, tmp_path):
    """便携/源码运行时数据跟着程序走，不污染用户数据目录。"""
    fake_app = tmp_path / "PortableApp"
    fake_app.mkdir()
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    assert resource_path.get_data_root() == fake_app
    assert not local_appdata.exists()


def test_log_dir_falls_back_when_logs_is_a_file(monkeypatch, tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "logs").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(app))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user"))

    directory = resource_path.get_log_dir()

    assert directory == tmp_path / "user" / "OfficeToolkit" / "logs"
    assert (app / "logs").read_text(encoding="utf-8") == "keep"


def test_nuitka_onefile_separates_external_data_and_internal_resources(monkeypatch, tmp_path):
    from types import SimpleNamespace

    executable_dir = tmp_path / "portable"
    extracted_dir = tmp_path / "unpacked"
    monkeypatch.setattr(
        resource_path, "__compiled__",
        SimpleNamespace(containing_dir=str(executable_dir)), raising=False,
    )
    monkeypatch.setattr(
        resource_path, "__file__", str(extracted_dir / "core" / "utils" / "resource_path.py"),
    )

    assert resource_path.get_app_root() == str(executable_dir)
    assert resource_path.get_resource_path("VERSION") == str(extracted_dir / "VERSION")


def test_logger_uses_user_directory_when_primary_resolution_fails(monkeypatch, tmp_path):
    import logging
    from contextlib import closing
    from core.utils import logger as logger_module

    def denied():
        raise PermissionError("primary directory denied")

    monkeypatch.setattr(logger_module, "get_log_dir", denied)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    with closing(logger_module.AppLogger._open_handler("fallback.log")) as handler:
        handler.handle(logging.LogRecord("audit", logging.INFO, "", 0, "kept", (), None))

    assert (tmp_path / "OfficeToolkit" / "logs" / "fallback.log").read_text(encoding="utf-8").strip() == "kept"

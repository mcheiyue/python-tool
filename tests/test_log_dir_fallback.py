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


def test_data_root_stays_next_to_app_when_writable(monkeypatch, tmp_path):
    """便携/源码运行时数据跟着程序走，不污染用户数据目录。"""
    fake_app = tmp_path / "PortableApp"
    fake_app.mkdir()
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    assert resource_path.get_data_root() == fake_app
    assert not local_appdata.exists()


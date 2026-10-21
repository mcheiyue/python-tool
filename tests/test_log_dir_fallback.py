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


def test_data_root_stays_next_to_app_when_writable(monkeypatch, tmp_path):
    """便携/源码运行时数据跟着程序走，不污染用户数据目录。"""
    fake_app = tmp_path / "PortableApp"
    fake_app.mkdir()
    local_appdata = tmp_path / "LocalAppData"
    monkeypatch.setattr(resource_path, "get_app_root", lambda: str(fake_app))
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    assert resource_path.get_data_root() == fake_app
    assert not local_appdata.exists()


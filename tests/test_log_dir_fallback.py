import pathlib

from core.utils import resource_path


def test_log_dir_falls_back_when_cwd_unwritable(monkeypatch, tmp_path):
    """装到 Program Files 后从安装目录启动时 CWD 不可写，日志目录必须回退而不是抛异常。"""
    real_mkdir = pathlib.Path.mkdir

    def deny_relative(self, *args, **kwargs):
        if not self.is_absolute():
            raise PermissionError(13, "denied", str(self))
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "mkdir", deny_relative)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    log_dir = resource_path.get_log_dir()

    assert log_dir.is_absolute()
    assert str(tmp_path) in str(log_dir)
    assert log_dir.is_dir()

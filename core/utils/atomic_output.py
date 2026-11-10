import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from core.cancellation import check_cancelled


@contextmanager
def atomic_output(
    destination: str | Path, *, should_cancel: Callable[[], bool] | None = None,
) -> Iterator[BinaryIO]:
    """同盘暂存，完整写入且未取消时才替换旧输出。"""
    target = Path(destination)
    check_cancelled(should_cancel)
    with TemporaryDirectory(prefix=f".{target.name}-", dir=target.parent) as staging:
        pending = Path(staging) / target.name
        with pending.open("wb") as stream:
            yield stream
        check_cancelled(should_cancel)
        os.replace(pending, target)

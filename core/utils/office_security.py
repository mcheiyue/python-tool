from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol


class OfficeApplication(Protocol):
    AutomationSecurity: int


@contextmanager
def macros_disabled(app: OfficeApplication) -> Iterator[None]:
    """仅在程序化打开文档期间禁止宏，并恢复应用原有安全设置。"""
    previous = app.AutomationSecurity
    app.AutomationSecurity = 3
    try:
        yield
    finally:
        app.AutomationSecurity = previous

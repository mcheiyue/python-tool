from collections.abc import Callable
from concurrent.futures import CancelledError


def check_cancelled(should_cancel: Callable[[], bool] | None) -> None:
    if should_cancel is not None and should_cancel():
        raise CancelledError()

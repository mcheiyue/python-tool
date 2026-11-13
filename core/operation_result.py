import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class OperationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _reject_non_serializable_data(data: dict[str, Any]) -> None:
    try:
        json.dumps(data, ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"OperationResult.data 必须可 JSON 序列化: {exc}") from exc


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: OperationStatus
    message: str
    outputs: tuple[str, ...] = ()
    succeeded: int = 0
    failed: int = 0
    data: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.data:
            _reject_non_serializable_data(self.data)

    @property
    def ok(self) -> bool:
        return self.status is OperationStatus.SUCCESS

    @classmethod
    def success(
        cls,
        message: str,
        *,
        outputs: tuple[str, ...] = (),
        succeeded: int = 0,
        failed: int = 0,
        data: dict[str, Any] | None = None,
    ) -> "OperationResult":
        return cls(OperationStatus.SUCCESS, message, outputs, succeeded, failed, data)

    @classmethod
    def failure(
        cls,
        message: str,
        *,
        outputs: tuple[str, ...] = (),
        succeeded: int = 0,
        failed: int = 1,
        data: dict[str, Any] | None = None,
    ) -> "OperationResult":
        return cls(OperationStatus.FAILED, message, outputs, succeeded, failed, data)

    @classmethod
    def cancelled(
        cls,
        message: str = "任务已取消",
        *,
        outputs: tuple[str, ...] = (),
        succeeded: int = 0,
        failed: int = 0,
        data: dict[str, Any] | None = None,
    ) -> "OperationResult":
        return cls(OperationStatus.CANCELLED, message, outputs, succeeded, failed, data)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status.value,
            "message": self.message,
            "outputs": list(self.outputs),
            "succeeded": self.succeeded,
            "failed": self.failed,
        }
        if self.data:
            payload["data"] = dict(self.data)
        return payload

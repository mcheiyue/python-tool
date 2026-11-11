from dataclasses import dataclass
from enum import Enum


class OperationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: OperationStatus
    message: str
    outputs: tuple[str, ...] = ()
    succeeded: int = 0
    failed: int = 0

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
    ) -> "OperationResult":
        return cls(OperationStatus.SUCCESS, message, outputs, succeeded, failed)

    @classmethod
    def failure(
        cls,
        message: str,
        *,
        outputs: tuple[str, ...] = (),
        succeeded: int = 0,
        failed: int = 1,
    ) -> "OperationResult":
        return cls(OperationStatus.FAILED, message, outputs, succeeded, failed)

    @classmethod
    def cancelled(
        cls,
        message: str = "任务已取消",
        *,
        outputs: tuple[str, ...] = (),
        succeeded: int = 0,
        failed: int = 0,
    ) -> "OperationResult":
        return cls(OperationStatus.CANCELLED, message, outputs, succeeded, failed)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "message": self.message,
            "outputs": list(self.outputs),
            "succeeded": self.succeeded,
            "failed": self.failed,
        }

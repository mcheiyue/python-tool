"""
BatchRunner — 全项目唯一的批处理循环（GLOSSARY: Batch Task）

纯 Python、零 Qt：批任务语义由遍历、停止旗标、逐项回调、成败统计组成；
Qt 信号协议由调用方用回调桥接（见 UI 层 WorkerThread 模式）。

回调签名（与现有信号协议对齐，供 R3-R5 迁移直接替换）：
    on_progress(current, total, name)   # 每个被尝试的项调用一次（尝试前）
    on_log(msg)
    should_stop() -> bool               # 每项尝试前检查，True 则停止

worker(item) 抛出异常计为 fail 且不中断循环；返回值语义由 worker 自定，本层忽略。
"""
from typing import Callable, Iterable, Optional, Tuple


def run(
    items: Iterable,
    worker: Callable,
    *,
    on_progress: Optional[Callable[[int, int, object], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> Tuple[int, int]:
    """执行批任务，返回 (success, fail)。"""
    items = list(items)
    total = len(items)
    success = fail = 0

    def log(msg: str):
        if on_log:
            on_log(msg)

    for idx, item in enumerate(items):
        if should_stop and should_stop():
            log("任务停止")
            break

        if on_progress:
            on_progress(idx + 1, total, item)

        try:
            worker(item)
            success += 1
        except Exception as e:
            fail += 1
            log(f"失败 {item}: {e}")

    return success, fail

"""BatchRunner 单元测试：全成功 / 含失败项继续 / 中途停止 / 回调为 None / 异常计数"""
import pytest

from core.batch import run


class TestBatchRunner:
    def test_all_success(self):
        seen_progress = []
        seen_log = []

        result = run(
            ["a", "b", "c"],
            lambda x: None,
            on_progress=lambda cur, total, name: seen_progress.append((cur, total, name)),
            on_log=seen_log.append,
        )

        assert result == (3, 0)
        assert seen_progress == [(1, 3, "a"), (2, 3, "b"), (3, 3, "c")]
        assert seen_log == []

    def test_partial_failure_continues(self):
        processed = []

        def worker(item):
            processed.append(item)
            if item == "bad":
                raise ValueError("boom")

        result = run(["ok1", "bad", "ok2"], worker)

        assert result == (2, 1)
        assert processed == ["ok1", "bad", "ok2"]  # 失败不中断，后续项继续

    def test_mid_batch_stop(self):
        processed = []
        seen_log = []

        result = run(
            [1, 2, 3, 4],
            lambda x: processed.append(x),
            on_log=seen_log.append,
            should_stop=lambda: len(processed) >= 2,
        )

        assert result == (2, 0)
        assert processed == [1, 2]
        assert "任务停止" in seen_log

    def test_callbacks_none(self):
        result = run([1, 2], lambda x: None)
        assert result == (2, 0)

        result = run([1, 2, 3], lambda x: None, should_stop=lambda: True)
        assert result == (0, 0)

    def test_worker_exception_counted(self):
        seen_log = []

        def worker(item):
            if item == "broken":
                raise RuntimeError("dead")
            return None  # 返回值被忽略

        result = run(["broken"], worker, on_log=seen_log.append)
        assert result == (0, 1)
        assert any("失败" in m and "dead" in m for m in seen_log)

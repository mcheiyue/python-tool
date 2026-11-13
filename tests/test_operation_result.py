import json

import pytest

from core.operation_result import OperationResult, OperationStatus


def test_operation_result_serializes_status_counts_and_outputs():
    result = OperationResult.success(
        "已完成",
        outputs=("out.pdf",),
        succeeded=1,
    )

    assert result.status is OperationStatus.SUCCESS
    assert result.ok
    assert result.to_dict() == {
        "status": "success",
        "message": "已完成",
        "outputs": ["out.pdf"],
        "succeeded": 1,
        "failed": 0,
    }
    assert json.loads(json.dumps(result.to_dict(), ensure_ascii=False))["outputs"] == ["out.pdf"]


def test_data_is_included_when_present():
    result = OperationResult.success(
        "提取到 2 种颜色",
        succeeded=1,
        data={"colors": [{"hex": "#ffffff"}, {"hex": "#000000"}], "backend": "pymupdf"},
    )

    assert result.to_dict()["data"] == {
        "colors": [{"hex": "#ffffff"}, {"hex": "#000000"}],
        "backend": "pymupdf",
    }


@pytest.mark.parametrize("empty", [None, {}])
def test_data_is_omitted_when_empty(empty):
    assert "data" not in OperationResult.success("已完成", data=empty).to_dict()


def test_non_serializable_data_is_rejected_at_construction():
    with pytest.raises(ValueError, match="JSON 序列化"):
        OperationResult.success("已完成", data={"value": object()})


def test_data_survives_json_roundtrip():
    result = OperationResult.failure(
        "部分失败",
        outputs=("a.pdf",),
        succeeded=1,
        failed=1,
        data={"backend": "libreoffice", "colors": []},
    )

    payload = json.loads(json.dumps(result.to_dict(), ensure_ascii=True))
    assert payload["data"] == {"backend": "libreoffice", "colors": []}
    assert payload["status"] == "failed"

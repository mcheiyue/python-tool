import json

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

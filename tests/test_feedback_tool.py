import pytest

from app.agent.tools.feedback_tool import FeedbackExtraction, FeedbackTool


def _tool() -> FeedbackTool:
    return FeedbackTool(email_service=None, admin_email="admin@example.com")  # type: ignore[arg-type]


def test_missing_fields_reports_all_when_empty():
    extraction = FeedbackExtraction(order_id=None, platform=None, message=None)
    missing = _tool().missing_fields(extraction)
    assert "order_id" in missing
    assert "platform (Swiggy or Zomato)" in missing
    assert "feedback" in missing


def test_missing_fields_empty_when_complete():
    extraction = FeedbackExtraction(
        order_id="SW123", platform="swiggy", message="Cake arrived late"
    )
    assert _tool().missing_fields(extraction) == []


@pytest.mark.asyncio
async def test_record_raises_when_fields_missing():
    extraction = FeedbackExtraction(order_id=None, platform=None, message=None)
    with pytest.raises(ValueError):
        await _tool().record("conv-1", extraction)

from app.agent.tools.feedback_tool import FeedbackExtraction, FeedbackTool
from app.models.feedback import FeedbackPlatform


def test_missing_fields_reports_all_when_empty():
    tool = FeedbackTool(repository=None)  # type: ignore[arg-type]
    extraction = FeedbackExtraction(order_id=None, platform=None, message=None)
    missing = tool.missing_fields(extraction)
    assert "order_id" in missing
    assert "platform (Swiggy or Zomato)" in missing
    assert "feedback" in missing


def test_missing_fields_empty_when_complete():
    tool = FeedbackTool(repository=None)  # type: ignore[arg-type]
    extraction = FeedbackExtraction(
        order_id="SW123", platform=FeedbackPlatform.SWIGGY, message="Cake arrived late"
    )
    assert tool.missing_fields(extraction) == []

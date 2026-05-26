from app.models import ReviewRequest


def test_default_target_level_is_l2():
    req = ReviewRequest(url="https://example.com")
    assert req.options.chinese_target_level == "L2"


def test_custom_target_level():
    req = ReviewRequest(url="https://example.com", options={"chinese_target_level": "L4"})
    assert req.options.chinese_target_level == "L4"

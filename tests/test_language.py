from app.services.language import detect_language_heuristic


def test_detects_hindi_devanagari_script():
    assert detect_language_heuristic("मुझे केक चाहिए") == "hi"


def test_detects_hinglish_by_keyword():
    assert detect_language_heuristic("cake ka price kya hai") == "hinglish"


def test_returns_none_for_plain_english():
    assert detect_language_heuristic("What cakes do you have?") is None


def test_returns_none_for_ambiguous_short_text():
    assert detect_language_heuristic("menu") is None

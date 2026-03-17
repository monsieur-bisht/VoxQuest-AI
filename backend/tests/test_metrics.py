from app.metrics import word_error_rate


def test_word_error_rate_exact_match():
    assert word_error_rate("hello tower", "hello tower") == 0.0


def test_word_error_rate_substitution():
    assert word_error_rate("hello tower", "hello forest") == 0.5

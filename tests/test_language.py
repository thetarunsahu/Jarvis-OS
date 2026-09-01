from core.language import normalize_for_routing


def test_hinglish_app_open_is_canonicalized():
    assert normalize_for_routing("Chrome kholo") == "open chrome"
    assert normalize_for_routing("Jarvis, VS Code khol do") == "open vscode"


def test_hinglish_volume_number_is_canonicalized():
    assert normalize_for_routing("volume tees percent kar do") == (
        "set volume to 30 percent"
    )
    assert normalize_for_routing("awaaz pachaas percent kar do") == (
        "set volume to 50 percent"
    )


def test_hindi_volume_number_is_canonicalized():
    assert normalize_for_routing("आवाज़ तीस प्रतिशत कर दो") == (
        "set volume to 30 percent"
    )


def test_hinglish_search_is_canonicalized():
    assert normalize_for_routing(
        "YouTube pe Interstellar soundtrack search karo"
    ) == "search youtube for interstellar soundtrack"


def test_explanatory_sentence_is_not_turned_into_action():
    text = "Can you explain why volume 30 percent sounds quiet?"
    assert normalize_for_routing(text) == (
        "can you explain why volume 30 percent sounds quiet"
    )


def test_negative_command_is_not_turned_into_action():
    text = "don't open chrome"
    assert normalize_for_routing(text) == "don't open chrome"

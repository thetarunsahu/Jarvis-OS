from __future__ import annotations

import re


_NUMBER_WORDS = {
    "zero": 0,
    "shunya": 0,
    "शून्य": 0,
    "das": 10,
    "दस": 10,
    "bees": 20,
    "बीस": 20,
    "tees": 30,
    "तीस": 30,
    "chalis": 40,
    "chaalis": 40,
    "चालीस": 40,
    "pachas": 50,
    "pachaas": 50,
    "पचास": 50,
    "saath": 60,
    "साठ": 60,
    "sattar": 70,
    "सत्तर": 70,
    "assi": 80,
    "अस्सी": 80,
    "nabbe": 90,
    "नब्बे": 90,
    "sau": 100,
    "सौ": 100,
}

_APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "क्रोम": "chrome",
    "notepad": "notepad",
    "नोटपैड": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "कैलकुलेटर": "calculator",
    "edge": "edge",
    "microsoft edge": "edge",
    "एज": "edge",
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "वीएस कोड": "vscode",
    "explorer": "explorer",
    "file explorer": "explorer",
    "फाइल एक्सप्लोरर": "explorer",
    "powershell": "powershell",
    "पावरशेल": "powershell",
    "terminal": "terminal",
    "टर्मिनल": "terminal",
    "cmd": "cmd",
    "command prompt": "cmd",
}


def normalize_for_routing(text: str) -> str:
    """Return a conservative canonical form for deterministic commands.

    Only high-confidence full-command shapes are rewritten. Arbitrary Hinglish
    conversation is deliberately left alone so the AI receives the user's
    original wording instead of an over-eager translation.
    """

    command = _clean(text)
    if not command:
        return ""

    command = re.sub(r"^(?:hey\s+)?jarvis[\s,]+", "", command).strip()
    command = re.sub(r"^(?:please|plz|pls)\s+", "", command).strip()

    app_match = re.fullmatch(
        r"(.+?)\s+(?:kholo|khol do|open karo|open kar do|खोलो|खोल दो|ओपन करो|ओपन कर दो)",
        command,
    )
    if app_match:
        target = _APP_ALIASES.get(app_match.group(1).strip())
        if target:
            return f"open {target}"

    volume_match = re.fullmatch(
        r"(?:volume|awaaz|aawaz|awaz|आवाज़|आवाज)\s+"
        r"([a-z\u0900-\u097f]+|\d{1,3})\s*"
        r"(?:%|percent|प्रतिशत)?\s*"
        r"(?:kar do|kar dena|set kar do|कर दो|कर देना)?",
        command,
    )
    if volume_match:
        value = _parse_number(volume_match.group(1))
        if value is not None and 0 <= value <= 100:
            return f"set volume to {value} percent"

    if re.fullmatch(
        r"(?:volume|awaaz|aawaz|awaz|आवाज़|आवाज)\s+"
        r"(?:badhao|badha do|increase karo|बढ़ाओ|बढ़ा दो)",
        command,
    ):
        return "volume up"

    if re.fullmatch(
        r"(?:volume|awaaz|aawaz|awaz|आवाज़|आवाज)\s+"
        r"(?:kam karo|ghatao|ghata do|decrease karo|कम करो|घटाओ|घटा दो)",
        command,
    ):
        return "volume down"

    if re.fullmatch(
        r"(?:mute|म्यूट)(?:\s+(?:kar do|kar dena|कर दो|कर देना))?",
        command,
    ):
        return "mute"

    youtube_match = re.fullmatch(
        r"(?:youtube|यूट्यूब)\s+(?:pe|par|पे|पर)\s+(.+?)\s+"
        r"(?:search karo|search kar do|सर्च करो|सर्च कर दो|khojo|खोजो)",
        command,
    )
    if youtube_match:
        return f"search youtube for {youtube_match.group(1).strip()}"

    google_match = re.fullmatch(
        r"(?:google|गूगल|web|वेब)\s+(?:pe|par|पे|पर)\s+(.+?)\s+"
        r"(?:search karo|search kar do|सर्च करो|सर्च कर दो|khojo|खोजो)",
        command,
    )
    if google_match:
        return f"search google for {google_match.group(1).strip()}"

    settings_match = re.fullmatch(
        r"(sound|audio|display|bluetooth|network|wifi|wi-fi|privacy|update)\s+"
        r"settings\s+(?:kholo|khol do|open karo|खोलो|खोल दो|ओपन करो)",
        command,
    )
    if settings_match:
        return f"open {settings_match.group(1)} settings"

    if re.fullmatch(
        r"(?:pc|computer|laptop|system)\s+(?:lock kar do|lock karo|लॉक कर दो|लॉक करो)",
        command,
    ):
        return "lock pc"

    if re.fullmatch(
        r"(?:shutdown|shut down|शटडाउन)(?:\s+(?:kar do|karo|कर दो|करो))?",
        command,
    ):
        return "shutdown"

    if re.fullmatch(
        r"(?:restart|रीस्टार्ट)(?:\s+(?:kar do|karo|कर दो|करो))?",
        command,
    ):
        return "restart"

    return command


def _parse_number(token: str) -> int | None:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)


def _clean(text: str) -> str:
    value = " ".join(str(text).strip().lower().split())
    return value.strip(" .!?।")

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InjectionSignal:
    code: str
    matched_text: str


_PATTERNS = {
    "IGNORE_INSTRUCTIONS": re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    "REVEAL_PROMPT": re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.I),
    "CROSS_USER_ACCESS": re.compile(r"access\s+another\s+user(?:'s|’s)?\s+data", re.I),
    "EXECUTE_COMMAND": re.compile(r"execute\s+this\s+command", re.I),
    "EXFILTRATE": re.compile(r"send\s+this\s+information\s+externally", re.I),
}


def detect_prompt_injection(text: str) -> list[InjectionSignal]:
    """Flag obvious review signals without declaring a document malicious."""
    signals: list[InjectionSignal] = []
    for code, pattern in _PATTERNS.items():
        if match := pattern.search(text):
            signals.append(InjectionSignal(code=code, matched_text=match.group(0)))
    return signals

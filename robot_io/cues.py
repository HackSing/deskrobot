"""反馈对应表：cue -> 表情行为、侧灯、动作。A 负责，到场后按设备实际可用的行为 ID 核对。

behavior: SDK 行为 ID（robot.behavior.play）。设备没有的 ID 会被跳过。
side: (颜色, 灯效)。灯效为 None 表示常亮；颜色为 None 表示不改。
tilt: 俯仰角序列（度），用来点头或低头。
"""
WHITE, BLUE, GREEN = "#DCE6F5", "#2F5BEA", "#2FA36B"

CUE_TABLE: dict[str, dict] = {
    "standby":         {"behavior": "standby",        "side": ("off", None)},
    "meeting_start":   {"behavior": "listening",      "side": (WHITE, None)},
    "idle":            {"behavior": "awake_idle",     "side": (WHITE, None)},
    "mark":            {"behavior": None,             "side": (WHITE, "blink"), "tilt": [-12, 0]},
    "thinking":        {"behavior": "thinking",       "side": (BLUE, "status_pulse")},
    "speaking":        {"behavior": "speaking",       "side": (WHITE, None)},
    "off_topic_soft":  {"behavior": "speechless",     "side": (None, None)},
    "off_topic_speak": {"behavior": "agent_question", "side": (WHITE, "breathing")},
    "overtime":        {"behavior": "shock",          "side": (None, None)},
    "confirm_ask":     {"behavior": "agent_question", "side": (WHITE, "breathing")},
    "confirm_ok":      {"behavior": "happy",          "side": (GREEN, "blink")},
    "loud":            {"behavior": "sad",            "side": (None, None), "tilt": [-15]},
}


def progress_color(ratio: float) -> tuple[str, str | None]:
    """底灯：进度 -> (颜色, 灯效)。"""
    if ratio < 0.5:
        return "#2FA36B", None
    if ratio < 1.0:
        return "#E8A623", None
    return "#E0503C", "blink"

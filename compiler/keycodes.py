"""
HID Keycode mappings for DuckyScript commands.
Maps DuckyScript key names to USB HID keycode constants used by the ESP32-S3 USB HID library.
"""

# Modifier keys (Arduino Keyboard.h constants)
MODIFIERS = {
    "CTRL":       "KEY_LEFT_CTRL",
    "CONTROL":    "KEY_LEFT_CTRL",
    "SHIFT":      "KEY_LEFT_SHIFT",
    "ALT":        "KEY_LEFT_ALT",
    "GUI":        "KEY_LEFT_GUI",
    "WINDOWS":    "KEY_LEFT_GUI",
    "COMMAND":    "KEY_LEFT_GUI",
    "SUPER":      "KEY_LEFT_GUI",
}

# Special keys
SPECIAL_KEYS = {
    "ENTER":        "KEY_RETURN",
    "RETURN":       "KEY_RETURN",
    "ESCAPE":       "KEY_ESC",
    "ESC":          "KEY_ESC",
    "BACKSPACE":    "KEY_BACKSPACE",
    "TAB":          "KEY_TAB",
    "SPACE":        "' '",
    "CAPSLOCK":     "KEY_CAPS_LOCK",
    "DELETE":       "KEY_DELETE",
    "DEL":          "KEY_DELETE",
    "INSERT":       "KEY_INSERT",
    "HOME":         "KEY_HOME",
    "END":          "KEY_END",
    "PAGEUP":       "KEY_PAGE_UP",
    "PAGEDOWN":     "KEY_PAGE_DOWN",
    "UPARROW":      "KEY_UP_ARROW",
    "UP":           "KEY_UP_ARROW",
    "DOWNARROW":    "KEY_DOWN_ARROW",
    "DOWN":         "KEY_DOWN_ARROW",
    "LEFTARROW":    "KEY_LEFT_ARROW",
    "LEFT":         "KEY_LEFT_ARROW",
    "RIGHTARROW":   "KEY_RIGHT_ARROW",
    "RIGHT":        "KEY_RIGHT_ARROW",
    "PRINTSCREEN":  "KEY_PRINT_SCREEN",
    "SCROLLLOCK":   "KEY_SCROLL_LOCK",
    "PAUSE":        "KEY_PAUSE",
    "BREAK":        "KEY_PAUSE",
    "NUMLOCK":      "KEY_NUM_LOCK",
    "MENU":         "KEY_MENU",
    "APP":          "KEY_MENU",
    "F1":           "KEY_F1",
    "F2":           "KEY_F2",
    "F3":           "KEY_F3",
    "F4":           "KEY_F4",
    "F5":           "KEY_F5",
    "F6":           "KEY_F6",
    "F7":           "KEY_F7",
    "F8":           "KEY_F8",
    "F9":           "KEY_F9",
    "F10":          "KEY_F10",
    "F11":          "KEY_F11",
    "F12":          "KEY_F12",
}

# All recognized keys (modifiers + special)
ALL_KEYS = {**MODIFIERS, **SPECIAL_KEYS}

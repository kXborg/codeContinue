"""Lightweight logging helpers for the CodeContinue plugin.

`_log` is gated by the `debug` setting so users opt in to chatter.
`_log_error` always prints — failures should be visible without enabling debug.
"""

import time

import sublime


def _log(msg):
    settings = sublime.load_settings("CodeContinue.sublime-settings")
    if settings.get("debug", False):
        ts = time.strftime('%H:%M:%S')
        print("CodeContinue [{0}] {1}".format(ts, msg))


def _log_error(msg):
    """Always prints, regardless of the debug setting."""
    ts = time.strftime('%H:%M:%S')
    print("CodeContinue [{0}] ERROR: {1}".format(ts, msg))

"""CodeContinue — Sublime Text 4 plugin entry point.

Sublime auto-loads top-level .py files in a package and registers any
sublime_plugin.* classes it finds in their namespace. This file imports the
plugin's commands, listeners, and the plugin_loaded hook from the submodules
under `utils/` so Sublime can discover them here.

Implementation lives in the submodules:
- utils/log.py         — _log / _log_error
- utils/text_utils.py  — pure text helpers (no Sublime deps)
- utils/api.py         — HTTP / auth helpers
- utils/settings.py    — settings discovery, first-run wizard, Configure command
- utils/suggest.py     — phantom inline-suggestion flow
- utils/chat.py        — chat-about-selection feature
"""

from .utils.settings import (  # noqa: F401
    CodeContinueConfigureCommand,
    plugin_loaded,
)
from .utils.suggest import (  # noqa: F401
    CodeContinueAcceptCommand,
    CodeContinueListener,
    CodeContinueSuggestCommand,
)
from .utils.chat import (  # noqa: F401
    ChatEventListener,
    CodeContinueChatCommand,
)

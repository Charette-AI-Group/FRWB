"""Telling Windows which application this process is.

Without this the taskbar groups the app under whatever started it and shows
that program's icon - for a pythonw launch, the Python icon - however good
the icon set is and however correctly Qt applies it. The window itself gets
the right icon either way, which is what makes the effect so confusing: the
title bar is right and the taskbar is wrong.

Windows keys the grouping on an Application User Model ID, and a process
that does not set one explicitly inherits the launcher's.
"""

from __future__ import annotations

import logging
import sys

from frwb import appConfig

logger = logging.getLogger(__name__)


def taskbarIdentity() -> str:
    """The AppUserModelID: vendor and application, as Windows expects."""
    return f"{appConfig.organizationName}.{appConfig.appShortName}"


def applyTaskbarIdentity() -> bool:
    """Claim the identity; say whether it was applied.

    False on anything that is not Windows, and on a Windows that refuses -
    neither is a failure worth stopping a launch for, and the only cost is
    the taskbar icon.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(taskbarIdentity())
    except (AttributeError, OSError) as exc:
        logger.info("Could not set the taskbar identity: %s", exc)
        return False
    return True

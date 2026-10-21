"""Keeps Windows awake while a job runs, the way a video player does; the power settings themselves are untouched.

On 21 Oct 2026 a power cut put the laptop on battery, which sleeps after 15 idle minutes, and the recorder
lost 73 minutes. The request covers sleep only (the screen may still turn off) and ends with the job.
"""

import contextlib
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _windows_set_state():
    if sys.platform != "win32":
        return None
    import ctypes

    return ctypes.windll.kernel32.SetThreadExecutionState


@contextlib.contextmanager
def keep_awake(set_state=None):
    """Hold a keep-awake request on this thread until the block exits. A no-op outside Windows."""
    set_state = set_state or _windows_set_state()
    if set_state is None:
        yield
        return
    set_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        yield
    finally:
        set_state(ES_CONTINUOUS)

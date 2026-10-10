"""Keep simulator workers from holding sockets after their parent crashes."""

import os
import signal
import sys


def follow_parent(parent_pid):
    if sys.platform == "linux":
        import ctypes
        # The death signal is set in the child; also close the race where the
        # parent died before this child had a chance to set PR_SET_PDEATHSIG.
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "Cannot set simulator parent death signal")
    return os.getppid() == parent_pid

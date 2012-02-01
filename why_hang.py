import inspect
import signal
import traceback

from twisted.internet import defer, task

# Usage: just import why_hang and stuff magically gets printed out if the main thread hangs. The hang time to trigger a traceback is somewhat probablistic. Worst case, the reactor hangs for MAX_DELAY seconds.

# These values are seconds
CANCEL_INTERVAL = 0.1
MAX_DELAY = 0.5


def reset_itimer():
    # TODO: change this to ITIMER_VIRTUAL for real-life usage
    signal.setitimer(signal.ITIMER_REAL, MAX_DELAY)


def log_traceback(signal, frame):
    # Oh snap, cancel_sigalrm didn't get called
    traceback.print_stack(frame)
    reset_itimer()


def cancel_sigalrm():
    # Cancel any pending alarm
    if signal.alarm(0) != 0:
        print "Previous alarm cancelled"
    else:
        print "No SIGALRM to cancel"
    reset_itimer()


# Handle SIGALRMs with print_traceback
signal.signal(signal.SIGALRM, log_traceback)


# this LoopingCall is run by the reactor.
# If the reactor is hung, cancel_sigalrm won't run and the handler for SIGALRM will fire
lc = task.LoopingCall(cancel_sigalrm)
lc.start(CANCEL_INTERVAL)

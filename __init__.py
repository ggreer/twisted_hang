import inspect
import signal
import traceback

from twisted.internet import defer, task

# Usage: just import why_hang and stuff magically gets printed out if the main thread hangs for more than MAX_DELAY seconds.

# These values are seconds
CANCEL_INTERVAL = 0.1
MAX_DELAY = 0.5


class WhyHang(object):
    def __init__(self):
        """docstring for __init__"""
        # Handle SIGALRMs with print_traceback
        signal.signal(signal.SIGALRM, self.log_traceback)


        # this LoopingCall is run by the reactor.
        # If the reactor is hung, cancel_sigalrm won't run and the handler for SIGALRM will fire
        self.lc = task.LoopingCall(self.cancel_sigalrm)
        self.lc.start(CANCEL_INTERVAL)

    def reset_itimer(self):
        # TODO: change this to ITIMER_VIRTUAL for real-life usage
        signal.setitimer(signal.ITIMER_REAL, MAX_DELAY)


    def log_traceback(self, signal, frame):
        # Oh snap, cancel_sigalrm didn't get called
        traceback.print_stack(frame)
        self.reset_itimer()


    def cancel_sigalrm(self):
        # Cancel any pending alarm
        if signal.alarm(0) == 0:
            print "No SIGALRM to cancel. This should only happen if we handled a traceback"
        self.reset_itimer()



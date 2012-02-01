import inspect
import signal
import traceback

from twisted.internet import task

# These values are seconds
CANCEL_INTERVAL = 0.1
MAX_DELAY = 0.5


class HangWatcher(object):
    def __init__(self, cancel_interval=CANCEL_INTERVAL, max_delay=MAX_DELAY):
        """docstring for __init__"""
        # Handle SIGALRMs with print_traceback
        signal.signal(signal.SIGALRM, self.log_traceback)

        # this LoopingCall is run by the reactor.
        # If the reactor is hung, cancel_sigalrm won't run and the handler for SIGALRM will fire
        self.lc = task.LoopingCall(self.cancel_sigalrm)
        self.cancel_interval = cancel_interval
        self.max_delay = MAX_DELAY

    def start(self):
        self.lc.start(self.cancel_interval)

    def reset_itimer(self):
        # TODO: change this to ITIMER_VIRTUAL for real-life usage
        signal.setitimer(signal.ITIMER_REAL, self.max_delay)

    def log_traceback(self, signal, frame):
        # Oh snap, cancel_sigalrm didn't get called
        # TODO: log stuff to a file or profiling data or whatever
        traceback.print_stack(frame)
        self.reset_itimer()

    def cancel_sigalrm(self):
        # Cancel any pending alarm
        if signal.alarm(0) == 0:
            print "No SIGALRM to cancel. This should only happen if we handled a traceback"
        self.reset_itimer()

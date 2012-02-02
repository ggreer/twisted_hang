import collections
import signal
import traceback

from twisted.internet import task

# These values are seconds
CANCEL_INTERVAL = 0.1
MAX_DELAY = 0.5


class HangWatcher(object):
    bad_functions = collections.defaultdict(int)
    hang_count = 0

    def __init__(self, cancel_interval=CANCEL_INTERVAL, max_delay=MAX_DELAY):
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
        signal.setitimer(signal.ITIMER_REAL, self.max_delay)

    def log_traceback(self, signal, frame):
        # Oh snap, cancel_sigalrm didn't get called
        traceback.print_stack(frame)

        self.hang_count += 1

        code_tuple = (frame.f_code.co_name, frame.f_code.co_filename, frame.f_code.co_firstlineno)
        self.bad_functions[code_tuple] += 1
        self.reset_itimer()

    def cancel_sigalrm(self):
        # Cancel any pending alarm
        signal.alarm(0)
        self.reset_itimer()

    def print_stats(self, reset_stats=False):
        print "Main thread was hung %s times" % self.hang_count

        # Don't print useless stuff below if there are no problems
        if self.hang_count == 0:
            return

        # This could be expensive
        bad_functions_list = self.bad_functions.items()
        bad_functions_list.sort(key=lambda x: x[1], reverse=True)

        print "Offending functions:"
        for func, count in bad_functions_list:
            print "%s %s in %s:%s" % (count, func[0], func[1], func[2])

        if reset_stats:
            self.reset_stats()

    def reset_stats(self):
        print "Resetting stats"
        self.hang_count = 0
        self.bad_functions.clear()

    def stats(self):
        stats_dict = {"hang_count": self.hang_count,
                      "bad_functions": self.bad_functions,
                     }

        return stats_dict

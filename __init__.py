import collections
import signal
import traceback

from twisted.internet import task

# These values are seconds
CANCEL_INTERVAL = 0.1
MAX_DELAY = 0.5


class HangWatcher(object):
    """
    Object which watches a L{twisted} reactor to determine whether the
    reactor is hung

    @ivar cancel_interval: how often to cancel the SIGALRM sent to the process
        (therefore this value should be less than C{max_delay})
    @type cancel_interval: C{int} or C{float}

    @ivar max_delay: how long to wait before determining that the reactor is
        hung (SIGALRM will be sent to the process after this much time, unless
        it is canceled, therefore C{cancel_interval} should be less than
        C{max_delay})
    @type max_delay: C{int} or C{float}

    @ivar bad_functions: a dictionary of bad functions that cause the
        reactor to hang, mapped to the number of times it has caused the
        reactor to hang
    @type bad_functions: C{dict} of C{tuples} to C{int}

    @ivar hang_count: number of times the reactor has been observed to be hung
    @type hang_count: C{int}

    @ivar currently_hung: whether the reactor was last seen to be hung
    @type currently_hung: C{bool}

    @ivar currently_bad_function: the code line that was last observed to have
        caused the reactor to hang
    @type: C{tuple} of the function name, file name, and first line number

    @ivar clock: the reactor to watch for hanging - if not set, will just use
        the default reactor (useful to be able to set for testing purposes)
    @type clock: L{twisted.internet.interfaces.IReactor} provider
    """

    hang_count = 0
    currently_hung = False

    def __init__(self, cancel_interval=CANCEL_INTERVAL, max_delay=MAX_DELAY):
        # Handle SIGALRMs with print_traceback
        signal.signal(signal.SIGALRM, self.log_traceback)

        # this LoopingCall is run by the reactor.
        # If the reactor is hung, cancel_sigalrm won't run and the handler for SIGALRM will fire
        self.lc = task.LoopingCall(self.cancel_sigalrm)

        self.cancel_interval = cancel_interval
        self.max_delay = max_delay

        self.bad_functions = collections.defaultdict(int)
        self.current_bad_function = ()

    def start(self):
        if self.clock is not None:
            self.lc.clock = self.clock
        self.lc.start(self.cancel_interval)

    def reset_itimer(self):
        signal.setitimer(signal.ITIMER_REAL, self.max_delay)

    def log_traceback(self, signal, frame):
        # Oh snap, cancel_sigalrm didn't get called
        traceback.print_stack(frame)

        self.currently_hung = True
        self.hang_count += 1

        self.current_bad_function = (frame.f_code.co_name,
                                     frame.f_code.co_filename,
                                     frame.f_code.co_firstlineno)
        self.bad_functions[self.current_bad_function] += 1
        self.reset_itimer()

    def cancel_sigalrm(self):
        # Cancel any pending alarm
        signal.alarm(0)
        # remove currently hung status
        self.currently_hung = False
        self.current_bad_function = ()
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

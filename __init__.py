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
        the default reactor (useful to be able to set for testing purposes) -
        be sure this is set before calling L{HangWatcher.start}
    @type clock: L{twisted.internet.interfaces.IReactor} provider

    @ivar hang_observers: list of callbacks to call when the reactor hangs
    @type hang_observers: C{list} of C{function}
    """

    hang_count = 0
    currently_hung = False
    clock = None

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

        self.hang_observers = []

    def add_hang_observer(self, callback):
        """
        Adds a hang observer, which is a callback to be called when the
        L{HangWatcher} notices that the reactor is hung.  It should take as an
        argument the current stack frame.

        @param callback: function to call when the L{HangWatcher} notices a
            reactor hang
        @type callback: C{function}

        @return: None
        """
        self.hang_observers.append(callback)

    def start(self):
        """
        Start watching the reactor for hangs.  If an alternate
        L{twisted.internet.interfaces.IReactor} provider should be watched,
        this instance's C{clock} property should be set to said provider
        before this function is called.

        @return: None
        """
        if self.clock is not None:
            self.lc.clock = self.clock
        self.lc.start(self.cancel_interval)

    def reset_itimer(self):
        """
        Starts a signal timer to signal the current process after C{max_delay}
        seconds.  If this process gets signaled, that means that the reactor
        failed to cancel the alarm, which means that the reactor has hung.
        """
        signal.setitimer(signal.ITIMER_REAL, self.max_delay)

    def log_traceback(self, signal, frame):
        """
        Record a reactor hang.  This means that the counter for the number of
        hangs is incremented, the counter for the number of hangs caused by
        a particular function is incremented for that function, and the
        current hang state is True (i.e. the reactor is currently hung).

        The timer is also reset so that the reactor will be checked again for
        hang status later.

        This function should not be called except for testing purposes.  The
        parameters are the parameters to a L{signal.signal} handler (see the
        L{signal.signal} documentaion)

        @param signal: the signal number
        @param frame: the current stack frame

        @return: None
        """
        # Oh snap, cancel_sigalrm didn't get called
        traceback.print_stack(frame)

        self.currently_hung = True
        self.hang_count += 1

        self.current_bad_function = (frame.f_code.co_name,
                                     frame.f_code.co_filename,
                                     frame.f_code.co_firstlineno)
        self.bad_functions[self.current_bad_function] += 1
        self.reset_itimer()

        # call all the observers
        for cb in self.hang_observers:
            cb(frame)

    def cancel_sigalrm(self):
        """
        Cancel the any current signal alarms, and resets the hang state of
        the reactor.  This function is supposed to be called by the reactor in
        a looping call every C{cancel_interval} seconds.  If the reactor is
        hung, this fails to get called, and hence a signal is sent to the
        process indicating that the reactor has hung.

        @return: None
        """
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

"""
Tests for L{twisted_hang.HangWatcher}
"""

import mock
import os
import signal

from twisted.internet.task import Clock
from twisted.trial.unittest import TestCase

import twisted_hang


class HangWatcherTestCase(TestCase):
    """
    Tests for L{twisted_hang.HangWatcher}
    """
    alarms = []

    def fake_setitimer(self, itimer_type, interval):
        """
        Sends a signal to the process after time has passed, according to the
        clock.  Note that this should be a different clock than what is used
        to simulate a hanging process.

        This otherwose follows the API of setitimer exactly with respect to
        which signals are sent based on which timer is used, raising a
        ItimerError when an invalid signal is passed or a negative time
        interval
        """
        if itimer_type == signal.ITIMER_REAL:
            sig = signal.SIGALRM
        elif itimer_type == signal.ITIMER_VIRTUAL:
            sig = signal.SIGVTALRM
        elif itimer_type == signal.ITIMER_PROF:
            sig = signal.SIGPROF
        else:
            # not very helpful, but the error raised by normal setitimer
            raise signal.ItimerError("[Errno 22] Invalid argument")

        if interval < 0:
            raise signal.ItimerError("[Errno 22] Invalid argument")

        def alarm():
            os.kill(os.getpid(), sig)

        self.alarms.append(
            self.itimer_clock.callLater(interval, alarm))

    def fake_signal_alarm(self, delay):
        """
        Cancels all alarms if delay is 0, otherwise schedules an alarm to be
        sent after C{delay} seconds
        """
        if delay == 0:
            alarms = self.alarms
            self.alarms = []
            for alarm in alarms:
                if alarm.active():
                    alarm.cancel()
        else:
            self.fake_setitimer(signal.ITIMER_REAL, delay)

    def advance_time(self, seconds, clocks):
        """
        Advances time incrementally, .5 seconds at a time, on all the clocks

        @param seconds: seconds to advance time
        @type seconds: C{int}

        @param clocks: list of clocks
        @type clocks: C{list}
        """
        for i in range(seconds * 2):
            for clock in clocks:
                clock.advance(.5)

    def setUp(self):
        # use task.Clock to simulate reactor hanging, and to simulate time
        # passing for setitimer
        self.fake_reactor = Clock()
        self.itimer_clock = Clock()

        # patch signal.setitimer and signal.alarm so that we can actually
        # control time passing
        self.patch(twisted_hang.signal, 'setitimer', self.fake_setitimer)
        self.patch(twisted_hang.signal, 'alarm', self.fake_signal_alarm)

        # patch traceback logging
        self.patch(twisted_hang, 'traceback', mock.Mock())

        # go with easy-to-type values
        self.watcher = twisted_hang.HangWatcher(1, 5)
        self.watcher.clock = self.fake_reactor

    def test_init_respects_delays_passed_to_it(self):
        """
        Cancel interval and max delay, if passed, should be respected
        """
        self.assertEqual(1, self.watcher.cancel_interval)
        self.assertEqual(5, self.watcher.max_delay)

    def test_init_has_valid_default_delays(self):
        """
        If no delays are passed, C{cancel_interval} and C{max_delay} should be
        set to a sane default where C{cancel_interval} < C{max_delay}
        """
        watcher = twisted_hang.HangWatcher()
        self.assertTrue(watcher.cancel_interval < watcher.max_delay)

    def test_logs_no_hangs_if_not_hung(self):
        """
        If the reactor isn't hung, the alarm should be canceled/should not
        alarm after C{max_delay}.  Which means that the reactor is not
        currently hung, the hang count is 0, and no bad functions have been
        recorded.
        """
        self.watcher.start()
        # time should advance on both the timer clock and the reactor
        self.advance_time(6, [self.fake_reactor, self.itimer_clock])

        self.assertEqual(0, self.watcher.hang_count)
        self.assertTrue(not self.watcher.currently_hung)
        self.assertEqual(0, len(self.watcher.bad_functions))
        self.assertEqual((), self.watcher.current_bad_function)

    def test_logs_hang_if_hung(self):
        """
        If the reactor is hung, the alarm never gets canceled and log_traceback
        should be called, which means that the reactor is currently hung,
        the hang count is 1, and a bad function has been recorded
        """
        self.watcher.start()
        # time should advance on the timer clock and the reactor is hung
        self.advance_time(6, [self.itimer_clock])

        self.assertEqual(1, self.watcher.hang_count)
        self.assertTrue(self.watcher.currently_hung)
        # one bad function should have been recorded
        self.assertEqual(1, len(self.watcher.bad_functions))
        # the bad function should be a tuple of the function name, the
        # filename, and the first line number of the function
        self.assertEqual(3, len(self.watcher.current_bad_function))

        bad_function = self.watcher.bad_functions.items()[0]
        # the bad function count for that particular function should be 1
        self.assertEqual(1, bad_function[1])
        # the bad function recorded should be the current bad function
        self.assertEqual(bad_function[0], self.watcher.current_bad_function)

    def tests_current_hung_status_gets_reset_if_reactor_unhangs_itself(self):
        """
        If the reactor is recorded as hung, but then unhangs itself, then the
        current hang status should be False.
        """
        self.watcher.start()
        # time should advance on the timer clock and the reactor is hung
        self.advance_time(6, [self.itimer_clock])

        # sanity check
        self.assertEqual(1, self.watcher.hang_count)
        self.assertTrue(self.watcher.currently_hung)
        # time should advance on both the timer clock and the reactor
        self.advance_time(6, [self.fake_reactor, self.itimer_clock])

        # the hang count should not have decreased
        self.assertEqual(1, self.watcher.hang_count)
        self.assertEqual(1, len(self.watcher.bad_functions))
        # the current state should be reset though
        self.assertTrue(not self.watcher.currently_hung)
        self.assertEqual((), self.watcher.current_bad_function)

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

        self.alarms.append(
            self.itimer_clock.callLater(interval, os.kill, os.getpid(), sig))

    def fake_signal_alarm(self, delay):
        """
        Cancels all alarms if delay is 0, otherwise schedules an alarm to be
        sent after C{delay} seconds
        """
        if delay == 0:
            alarms = self.alarms
            self.alarms = []
            for alarm in alarms:
                alarm.cancel()
        else:
            self.fake_setitimer(signal.ITIMER_REAL, delay)

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

    # def test_logs_no_hangs_if_not_hung(self):
    #     """
    #     If the reactor isn't hung, the alarm should be canceled/should not
    #     alarm after C{max_delay}
    #     """
    #     self.watcher.start()
    #     self.fake_reactor.advance(6)
    #     self.itimer_clock.advance(6)
    #     self.assertEqual(0, self.watcher.hang_count)

    # def test_logs_hang_if_hung(self):
    #     """
    #     If the reactor is hung, the alarm never gets canceled and log_traceback
    #     should be called
    #     """
    #     self.watcher.start()
    #     self.itimer_clock.advance(6)
    #     self.assertEqual(1, self.watcher.hang_count)

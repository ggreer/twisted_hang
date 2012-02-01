import inspect
import signal
import traceback

from twisted.internet import defer, task

# Usage: just import why_hang and stuff magically gets printed out if the main thread hangs for > .01 seconds

SIGALRM_INTERVAL = 0.1 # seconds

def print_traceback(signal, frame):
    # Oh snap, we didn't
    traceback.print_stack(frame)
    #import pdb; pdb.set_trace()

def cancel_sigalrm_and_set_itimer():
    # Cancel any pending alarm
    if signal.alarm(0) != 0:
        print "Previous alarm cancelled"
    else:
        print "No SIGALRM to cancel"
    # Send SIGALRM every 0.11 seconds
    # TODO: change this to ITIMER_VIRTUAL for real-life usage
    signal.setitimer(signal.ITIMER_REAL, SIGALRM_INTERVAL + 0.01)

# Handle SIGALRMs with print_traceback
signal.signal(signal.SIGALRM, print_traceback)

lc = task.LoopingCall(cancel_sigalrm_and_set_itimer)
lc.start(SIGALRM_INTERVAL)

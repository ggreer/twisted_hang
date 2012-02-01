import inspect
import signal
import traceback

def print_traceback(signal, frame):
    traceback.print_stack(frame)
    #import pdb; pdb.set_trace()

# Handle SIGALRMs with print_traceback
signal.signal(signal.SIGALRM, print_traceback)

# Usage
    from twisted_hang import HangWatcher
    blah = HangWatcher(0.1, 0.5) # these params are optional. They have sane defaults
    blah.start()

Stuff will magically get printed out if the main thread hangs for more than MAX_DELAY seconds.

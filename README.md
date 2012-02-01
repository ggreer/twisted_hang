# Usage
    from twisted_hang import HangWatcher
    watcher = HangWatcher(0.1, 0.5) # these params are optional. They have sane defaults
    watcher.start()

Stuff will magically get printed out if the main thread hangs for more than MAX_DELAY seconds. If you want more info, look at the dict returned by `watcher.stats()`.

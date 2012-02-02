# Usage
    from twisted_hang import HangWatcher
    watcher = HangWatcher(0.1, 0.5) # these params are optional. They have sane defaults
    watcher.start()

Stuff will magically get printed out if the main thread hangs for more than MAX_DELAY seconds. If you want more info, add something like this after the lines above:

    from twisted.internet import task
    # Print stats every 60 seconds
    lc = task.LoopingCall(watcher.print_stats)
    lc.start(60)

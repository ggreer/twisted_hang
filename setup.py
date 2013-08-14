#!/usr/bin/env python

from distutils.core import setup

__version__ = "0.1"

setup(name="twisted_hang",
      version=__version__,
      description="Figure out if the main thread is hanging, and if so, what's causing it to hang.",
      author="Geoff Greer",
      license="MIT",
      url="https://github.com/ggreer/twisted_hang",
      download_url="https://github.com/ggreer/twisted_hang.git",
      )

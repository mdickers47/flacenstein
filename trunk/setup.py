#!/usr/bin/python

from distutils.core import setup

setup(name='flacenstein',
      version='0.1',
      description='FLAC librarian and transcoder',
      author='Michael A. Dickerson',
      author_email='mikey@singingtree.com',
      url='http://obstrepero.us/hacks/flac/flacenstein',
      packages=['flacenstein'],
      scripts=['flac-lint', 'flac-combine', 'flacapp.py']
      )

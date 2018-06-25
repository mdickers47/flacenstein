#!/usr/bin/python
"""
flac-repair-cuesheet.py - Convert "INDEX 01 10161816" to "INDEX 01 xx:yy:zz"
in the input stream.  This is to cope with metaflac's brain damage where its
output format is not compatible with its own input parser.  Kickass.
"""
from flacenstein import flaclib
import re
import sys

regex = re.compile('^(.*)INDEX (\d+) (\d+)$')

for line in sys.stdin:
  m = regex.search(line)
  if m:
    frames, slop = divmod(long(m.group(3)), flaclib.CD_SAMPLES_PER_FRAME)
    assert slop == 0
    secs, frames = divmod(frames, 75)
    mins, secs = divmod(secs, 60)
    sys.stdout.write(m.group(1))
    sys.stdout.write('INDEX ')
    sys.stdout.write(m.group(2))
    sys.stdout.write(' %02d:%02d:%02d\n' % (mins, secs, frames))
  else:
    sys.stdout.write(line)


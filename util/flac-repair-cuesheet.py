#!/usr/bin/python
"""
flac-repair-cuesheet.py - Convert "INDEX 01 10161816" to "INDEX 01 xx:yy:zz"
in the input stream.  This is to cope with metaflac's brain damage where its
output format is not compatible with its own input parser.  Kickass.
"""
import re
import sys

CD_SAMPLES_PER_FRAME = 588
idx_regex = re.compile('^(.*)INDEX (\d+) (\d+)$')
out_regex = re.compile('^REM FLAC__lead-out (\d+) (\d+)$')

for line in sys.stdin:
  m = idx_regex.match(line)
  if m:
    frames, slop = divmod(long(m.group(3)), CD_SAMPLES_PER_FRAME)
    assert slop == 0
    secs, frames = divmod(frames, 75)
    mins, secs = divmod(secs, 60)
    line = (m.group(1) + 'INDEX ' + m.group(2)
            + ' %02d:%02d:%02d\n' % (mins, secs, frames))

  # for some inexplicable reason, the flac parser in golang enforces
  # that the lead-out "track" is 170 if the isCompactDisc flag is true,
  # and 255 otherwise.  metaflac will set isCompactDisc=false if the
  # stream length is not 0 mod 588.
  m = out_regex.match(line)
  if m:
    assert m.group(1) == '170'
    if long(m.group(2)) % CD_SAMPLES_PER_FRAME != 0:
      sys.stderr.write('stream length is not CD-DA compliant\n')
      line = 'REM FLAC__lead-out 255 %s' % m.group(2)

  sys.stdout.write(line)


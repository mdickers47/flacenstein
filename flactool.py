#!/usr/bin/env python
"""Usage: flactool.py [-options] verb [args]

Options apply to multiple verbs:

-t abc  - Set output type (see 'check' below).
-o path - Set output file path.
-l lib  - Use lib instead of default library file.
-0      - Write output to stdout with null delimiters.

There must be exactly one verb, which may have arguments:

init path1 path2 ...
  Create new library file with one or more root paths.

check
  Print configuration and self-tests.  Transcoder modules that report
  "ready" can be used as an argument to -t.

scan
  Search filesystem and update library index with any new, changed, or
  deleted flac files.

search flacarg1 flacarg2 ...
  Print absolute paths of selected flac files.  With -0, you can pipe
  the output to e.g. "xargs -0 -n 1 mplayer"

info flacarg1 flacarg2 ...
  Print metadata tags for selected flac files.

extract flacarg1 tracknum
  Extract given track from flac file to a wav file in current
  directory.

latest n
  Print absolute paths of the n files with the most recent modification
  times.

convert flacarg1 flacarg2 ...
  Transcode selected flac files.  Output type and path are controlled
  by -t and -o.  The last-used values are remembered if not specified.
  Any file that already exists at a desired output path will not be
  overwritten.

Any flacarg may be either a resolvable file name, or a regex that will
be matched against filenames, artists, and album tags in the entire
library.

Copyright 2009-2017 Mikey Dickerson.  Modification and redistribution
are permitted under the terms of the GNU General Public License,
version 2.
"""

import Queue
import getopt
import os
import re
import sys
import tempfile
import threading

import flacenstein.flaclib as flaclib
import flacenstein.flaccfg as flaccfg


class Error(Exception): pass

def usage(msg=None):
  if msg: sys.stderr.write(msg + '\n')
  sys.stderr.write(__doc__ + '\n')
  sys.exit(1)


def import_xfm(xfm):
  try:
    xfmmod = __import__('flacenstein.xfm%s' % xfm, globals(),
                        locals(), 'xfm%s' % xfm)
  except ImportError:
    print '%s can\'t be imported' % xfm
    xfmmod = None
  return xfmmod


def parse_flac_args(lib, args):
  assert type(args) == type([]) # watch out for strings!
  flacs = []
  for arg in args:
    if os.path.isfile(arg):
      flacs.append(flaclib.FlacFile(arg))
    else:
      regex = re.compile(arg, re.IGNORECASE)
      for flac in lib.flacs.values():
        if (regex.search(flac.filename) or
            regex.search(flac.artist or "") or
            regex.search(flac.album or "")):
            flacs.append(flac)
  return flacs


def print_stdout(what, null_delimiter=False):
  if null_delimiter:
    sys.stdout.write(what)
    sys.stdout.write('\0')
  else:
    print what


class TranscodeWorker(threading.Thread):

  def __init__(self, queue, xfmmod, myname):
    threading.Thread.__init__(self)
    self.queue = queue
    self.xfmmod = xfmmod
    self.myname = myname

  def run(self):
    while not self.queue.empty():
      job = self.queue.get()
      child = os.fork()
      if child == 0:
        # encodeFile() is expected to exec an encoder process and
        # exit with a status code.
        self.xfmmod.encodeFile(job)
        assert False, 'Unpossible! encodeFile() returned!'

      try:
        os.waitpid(child, 0)
      except KeyboardInterrupt:
        print 'Killing child process %s' % child
        os.kill(child, 15)
        print 'See You Space Cowboy'
        return

      self.queue.task_done()
      print 'worker %s finished %s' % (self.myname, job.outfile)


def transcode_flacs(flaclist, prefs):

  if not prefs['output_path'] and prefs['output_type']:
    raise Error('must specify output path and type')

  xfmmod = import_xfm(prefs['output_type'])
  xfmmod.outpath = prefs['output_path']
  if not xfmmod.ready():
    raise Error('%s module failed self-tests' % prefs['output_type'])

  print 'output type is %s' % xfmmod.description
  artdir = tempfile.mkdtemp('', 'flacart.')
  jobq = Queue.Queue()
  class EncodeJob: pass

  for f in flaclist:
    for c, t in enumerate(f.tracks):
      j = EncodeJob()
      j.tracknum = c + 1
      j.artist = f.artist
      j.title = t or 'Track %d' % j.tracknum
      j.album = f.album
      j.flacfile = f.filename
      j.coverart = f.extractThumbnail(artdir)
      fname = '%02d %s.%s' % (j.tracknum, t, xfmmod.extension)
      j.outfile = os.path.join(prefs['output_path'],
                               flaclib.filequote(f.artist),
                               flaclib.filequote(f.album),
                               flaclib.filequote(fname))
      j.failures = 0
      if not os.path.isfile(j.outfile): jobq.put(j)

  print 'Prepared %d jobs' % jobq.qsize()
  bag_o_threads = set()
  while len(bag_o_threads) < prefs.get('threads', 1):
    t = TranscodeWorker(jobq, xfmmod, len(bag_o_threads))
    t.start()
    bag_o_threads.add(t)

  # we wait for all the threads to exit, rather than wait for the
  # queue to be empty, because the worker threads might crash.
  while bag_o_threads:
    t = bag_o_threads.pop()
    t.join()


if __name__ == '__main__':

  library_file = flaccfg.DEFAULT_LIBRARY
  print_nulls = False
  lib = flaclib.FlacLibrary([])
  prefs = {}
  state_dirty = False

  try:
    opts, args = getopt.getopt(sys.argv[1:], 't:o:l:0j:')
    opts = dict(opts)
  except getopt.GetoptError, e:
    sys.stderr.write(str(e) + '\n')
    usage()

  # look for -l option first, then read preferences from it,
  # then process other options.
  if '-l' in opts: library_file = opts['-l']

  try:
    lib, prefs = flaclib.loadSavefile(library_file)
  except (EOFError, IOError):
    sys.stderr.write('Failed to load %s\n' % library_file)

  if '-t' in opts:
    prefs['output_type'] = opts['-t']
    state_dirty = True

  if '-o' in opts:
    prefs['output_path'] = opts['-o']
    state_dirty = True

  if '-j' in opts:
    try:
      prefs['threads'] = int(opts['-j'])
    except ValueError:
      usage('non-integer argument for threads: %s' % opts['-j'])
    state_dirty = True

  if '-0' in opts:
    print_nulls = True

  if len(args) < 1: usage()
  verb = args[0]

  if verb == 'check':

    print 'Library %s contains %s files' % (library_file, len(lib.flacs))
    print 'Library root paths are: %s' % lib.rootpaths
    print 'Last used output path is: %s' % prefs.get('output_path', '')
    print 'Last used output type is: %s' % prefs.get('output_type', '')
    flaclib.testBinaries()
    print 'Transcoder self-tests:'
    for xfm in flaccfg.XFM_MODS:
      xfmmod = import_xfm(xfm)
      if xfmmod and xfmmod.ready():
        print '%s module is ready' % xfm
      else:
        print '%s failed self-tests and is disabled.' % xfm
      del xfmmod

  elif verb == 'init':

    # throw away the lib object we might already have
    lib = flaclib.FlacLibrary(args[1:])
    lib.scan()
    state_dirty = True

  elif verb == 'scan':

    lib.scan()
    state_dirty = True

  elif verb == 'update_tags':

    # There is no "standard" for vorbis tags, so the useful form has varied
    # over time.  flaclib understands more than one variant, but always
    # generates the current "canonical" form when you call saveTags().  So
    # this is a cheap way to bring old-form tags up to date.
    to_update = parse_flac_args(lib, args[1:])
    for flac in to_update:
      print 'Rewriting tags for %s' % flac.filename
      flac.saveTags(preserve_mtime=True)

  elif verb == 'search':

    flacs = parse_flac_args(lib, args[1:])
    for f in flacs: print_stdout(f.filename, print_nulls)

  elif verb == 'extract':

    flacs = parse_flac_args(lib, [args[1]])
    # people typically expect track numbers to be 1-based
    tracknum = int(args[2]) - 1
    if len(flacs) != 1:
      print 'Argument %s must match 1 file in library, not %d' % \
        (args[1], len(flacs))
      sys.exit(1)
      flacs[0].extractTrack(tracknum)

  elif verb == 'latest':

    n = 10
    if len(args) > 1:
      try:
        n = int(args[1])
      except ValueError:
        usage()

    flacs = lib.flacs.values()
    flacs.sort(key=lambda f: f.mtime, reverse=True)
    for f in flacs[:n]: print_stdout(f.filename, print_nulls)

  elif verb == 'info':

    flacs = parse_flac_args(lib, args[1:])
    for f in flacs:
      print '===> %s' % f.filename
      print 'Artist: %s' % f.artist
      print 'Album: %s' % f.album
      print 'Date: %s' % f.date
      for n, t in enumerate(f.tracks): print 'Track %d: %s' % (n+1, t)

  elif verb == 'convert':

    to_convert = parse_flac_args(lib, args[1:])
    transcode_flacs(to_convert, prefs)

  else:
    usage()

  if state_dirty: flaclib.writeSavefile(library_file, lib, prefs)
  sys.exit(0)


#!/usr/bin/python
"""
Usage: flactool.py [-t output_type] [-o output_path] [-l library_path]
                   ( check | 
                     init path1 path2 ... |
                     scan |
                     convert flac1 flac2 ... |
                     search flac1 flac2 ... |
                     info flac1 flac2 ... |
                     extract flac1 tracknum )

See output of 'flactool check' for possible output types.

Use 'flactool init /path/to/flacs' to create a new library file in the
default location.  Use 'flactool scan' to update the library when
files are added or deleted.

Any argument specifying a flac file name may be either an explicit path
name, or a regex that will be matched against filenames, artists, and
album names in the whole library.

Copyright 2009 Michael A. Dickerson.  Modification and redistribution
are permitted under the terms of the GNU General Public License,
version 2.
"""

import getopt
import os
import re
import sys
import tempfile

import flacenstein.flaclib as flaclib
import flacenstein.flaccfg as flaccfg

xfmmod = None

def usage():
  print __doc__
  sys.exit(1)

def import_xfm(xfm):
  global xfmmod
  try:
    xfmmod = __import__('flacenstein.xfm%s' % xfm, globals(),
                        locals(), 'xfm%s' % xfm)
  except ImportError:
    print '%s can\'t be imported' % xfm
    xfmmod = None

def parse_flac_args(lib, args):
  assert type(args) == type([]) # watch out for strings!
  flacs = []
  for arg in args:
    if os.path.isfile(arg):
      flacs.append(flaclib.FlacFile(arg))
    else:
      regex = re.compile(arg)
      for flac in lib.flacs.values():
        if (regex.search(flac.filename) or
            regex.search(flac.artist or "") or
            regex.search(flac.album or "")):
            #print 'regex %s selected %s' % (arg, flac.filename)
            flacs.append(flac)
    return flacs

if __name__ == '__main__':

    library_path = flaccfg.DEFAULT_LIBRARY
    output_path = None
    output_type = 'mp3_art'
    lib = flaclib.FlacLibrary('')
    lib_dirty = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], 't:o:l:')
    except getopt.GetoptError, e:
        print str(e)
        usage()
    for (opt, val) in opts:
        if opt == '-t':
            output_type = val
        elif opt == '-o':
            output_path = val
        elif opt == '-l':
            library_path = val
        else:
            assert False, 'unpossible!'
    if len(args) < 1: usage()

    # Load library file, though we may not need it
    try:
        lib.flacs, lib.rootpaths, saved_path = \
            flaclib.loadSavefile(library_path)
    except (EOFError, IOError):
        print 'Failed to load %s' % library_path
        saved_path = None

    if output_path and output_path != saved_path:
        lib_dirty = True
    elif not output_path:
        output_path = saved_path

    verb = args[0]   
    if verb == 'check':

        print 'Library %s contains %s files' % (library_path, len(lib.flacs))
        print 'Library root paths are: %s' % lib.rootpaths
        print 'Last used output path is: %s' % output_path
        flaclib.testBinaries()
        print 'Following are results from transcoder self-tests:'
        for xfm in flaccfg.XFM_MODS:
            import_xfm(xfm)
            if xfmmod and xfmmod.ready():
                print '%s module is ready' % xfm
            else:
                print '%s failed self-tests and is disabled.' % xfm

    elif verb == 'init':

        lib.rootpaths = args[1:]
        lib.scan()
        lib_dirty = True

    elif verb == 'scan':

        lib.scan()
        lib_dirty = True

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
        for f in flacs:
          print f.filename

    elif verb == 'extract':

        flacs = parse_flac_args(lib, [args[1]])
        # people typically expect track numbers to be 1-based
        tracknum = int(args[2]) - 1
        if len(flacs) != 1:
          print 'Argument %s must match 1 file in library, not %d' % \
              (args[1], len(flacs))
          sys.exit(1)
        flacs[0].extractTrack(tracknum)

    elif verb == 'info':

        flacs = parse_flac_args(lib, args[1:])
        for f in flacs:
          print '===> %s' % f.filename
          print 'Artist: %s' % f.artist
          print 'Album: %s' % f.album
          print 'Date: %s' % f.date
          for n, t in enumerate(f.tracks):
              print 'Track %d: %s' % (n+1, t)


    elif verb == 'convert':

        to_convert = parse_flac_args(lib, args[1:])
        import_xfm(output_type)
        print 'output type is %s' % xfmmod.description
        xfmmod.outpath = output_path
        if not xfmmod.ready():
            print '%s module fails self-tests.' % output_type
            sys.exit(1)

        artdir = tempfile.mkdtemp('', 'flacart.')
        jobs = []
        class EncodeJob: pass

        for f in to_convert:
            c = 0
            for t in f.tracks:
                c += 1
                j = EncodeJob()
                j.artist = f.artist
                j.title = t or 'Track %d' % c
                j.album = f.album
                j.tracknum = c
                j.flacfile = f.filename
                j.coverart = f.extractThumbnail(artdir)
                # j.listindex = f.listindex
                fname = '%02d - %s.%s' % (c, t, xfmmod.extension)
                j.outfile = os.path.join(output_path,
                                         flaclib.filequote(f.artist),
                                         flaclib.filequote(f.album),
                                         flaclib.filequote(fname))
                j.failures = 0
                if not os.path.isfile(j.outfile): jobs.append(j)

        print 'Prepared %d jobs' % len(jobs)
        while jobs:
            j = jobs.pop()
            child = os.fork()
            if child == 0:
                # encodeFile() is expected to exec an encoder process and
                # exit with a status code.
                xfmmod.encodeFile(j)
                assert False, 'Unpossible! encodeFile() returned!'
            try:
                os.waitpid(child, 0)
            except KeyboardInterrupt:
                print 'Killing child process %s' % child
                os.kill(child, 15)
                print 'See you space cowboy'
                break

            if len(jobs) % 10 == 0: print '\n===> %d jobs to go\n' % len(jobs)
    else:
        usage()


    if lib_dirty:
        flaclib.writeSavefile(library_path, lib.flacs, lib.rootpaths,
                              output_path)


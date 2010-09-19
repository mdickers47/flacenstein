"""
Classes for FLAC files and FLAC libraries (which are just collections
of FLAC files).

Copyright (C) 2005 Michael A. Dickerson.  Modification and
redistribution are permitted under the terms of the GNU General Public
License, version 2.
"""
import os
import pickle
import re
import stat
import sys
import tempfile

CD_SAMPLES_PER_FRAME = 588 # 44100 samples/sec / 75 frames/sec

SIMPLE_TAGS = ['ARTIST', 'ALBUM', 'DATE', 'GENRE', 'ARCHIVE',
               'TRACKNUM', 'RIPSTATUS']

class Error(Exception): pass
class MetaflacFailed(Error): pass
class BadMetadata(Error): pass


class FlacFile:
    """
    A class representing a single FLAC file, which may represent zero or
    more tracks.  Tracks are the atoms that will be encoded in destination
    formats that assume one song per file (e.g. mp3, m4a, basically everything
    except FLAC.)
    """
    
    def __init__(self, fname):
      # We fake the appearance of attributes like self.artist by keeping
      # them in self.tags and implementing __getattr__() and __setattr__().
      # Beware that if you assign to anything else before self.tags, you will
      # create infinite recursion in __getattr__ and crash.
      self.tags = {}
      for tag in SIMPLE_TAGS: self.tags[tag] = None

      # initialize everything so that we don't die with attribute not
      # found errors
      self.filename = fname

      self.tracks = []
      self.md5 = None
      self.selected = False
      self.length = 0
      self.coverart = ''
      self.archive = ''
      self.channels = None
      self.bits_per_sample = None
      self.samples = None
      self.sample_rate = None
      self.mtime = None

      if fname is not None and os.path.exists(fname): self.getMetadata()

    def _flac_cmd(self, flag, stdin=None):
      cmd = 'metaflac --%s -- %s' % (flag, shellquote(self.filename))
      if stdin:
        metaflac = os.popen(cmd, 'w')
        metaflac.write(stdin)
        # metaflac tends to ignore the last line if it doesn't end with \n.
        if not stdin.endswith('\n'): metaflac.write('\n')
        out = None
      else:
        metaflac = os.popen(cmd)
        out = metaflac.read().split('\n')
      ret = metaflac.close()
      if ret: raise MetaflacFailed('%s returned %s' % (cmd, ret))
      return out

    def getMetadata(self):
      for l in self._flac_cmd('list'):
        tokens = l.split(':', 1)
        if len(tokens) == 1:
          field, arg = tokens[0].strip(), None
        else:
          field, arg = [ x.strip() for x in tokens ]
        if field == 'channels': self.channels = int(arg)
        elif field == 'bits-per-sample': self.bits_per_sample = int(arg)
        elif field == 'total samples': self.samples = int(arg)
        elif field == 'MD5 signature': self.md5 = arg
        elif field == 'sample_rate': self.sample_rate = int(arg.split()[0])
        elif field.startswith('comment['):
          c, arg = [ x.strip() for x in arg.split('=', 1) ]
          # A few tags have been discovered to need special handling over
          # time.  Everything else gets dumped in self.tags untouched.
          if c in ('ARTIST', 'ALBUM', 'ARCHIVE'):
            self.tags[c] = unicode(arg, 'utf8')
          elif c.startswith('TITLE'): self.tracks.append(unicode(arg, 'utf8'))
          elif c == 'TRACKNUM': self.tags[c] = int(arg)
          # save random crap we don't parse in self.tags
          else: self.tags[c] = arg

      # Record mtime before we mess with the file, because sometimes we
      # are going to want to set it back to what it was.
    def getFrames(self):
      return self.samples / CD_SAMPLES_PER_FRAME

    def saveTags(self, preserve_mtime=False):

      if preserve_mtime:
        st = os.stat(self.filename)
        utime = (st[stat.ST_ATIME], st[stat.ST_MTIME])

      tag_names = self.tags.keys()
      # TITLE is the only place where we preserve order, so its behavior is
      # different.  self.tags['TITLE'] should not be set, and only self.tracks
      # is used.
      if 'TITLE' in tag_names:
        sys.stderr.write('Warning: TITLE was found in tags dictionary!\n')
        tag_names.remove('TITLE')

      # Sort the tags list to match the order given in SIMPLE_TAGS.  Random
      # other tags are sorted asciibetically.
      def cmp_tag_names(a, b):
        if a in SIMPLE_TAGS and b in SIMPLE_TAGS:
          return cmp(SIMPLE_TAGS.index(a), SIMPLE_TAGS.index(b))
        elif a in SIMPLE_TAGS:
          return -1
        elif b in SIMPLE_TAGS:
          return 1
        else:
          return cmp(a, b)

      tag_names.sort(cmp=cmp_tag_names)
      t = [ '%s=%s' % (name, self.tags[name]) for name in tag_names 
            if self.tags[name] ] # Drop tags with '' or None values
      for i in xrange(len(self.tracks)):
        t.append('TITLE[%d]=%s' % (i + 1, self.tracks[i]))
      self._flac_cmd('remove-all-tags --import-tags-from=-',
                     stdin='\n'.join(t).encode('utf8'))

      if preserve_mtime: os.utime(self.filename, utime)

    def __getattr__(self, name):
      # If you ask for anything like self.artist that isn't a real attribute,
      # look in the self.tags dict for something called 'ARTIST'.
      if 'tags' in self.__dict__ and name.upper() in self.tags:
        return self.tags[name.upper()]
      else:
        raise AttributeError, "'FlacFile' object has no attribute '%s'" % name

    def __setattr__(self, name, val):
      # Intercept attempts to set e.g. self.artist which are really tags.
      if 'tags' in self.__dict__ and name.upper() in self.tags:
        self.tags[name.upper()] = val
      else:
        self.__dict__[name] = val  

    def saveCuesheet(self, cuesheet):
      self._flac_cmd('import-cuesheet-from=-', stdin=cuesheet)

    def suggestFilename(self):
      return filequote('%s - %s.flac' % (self.artist,
                                         self.album or self.tracks[0])).strip()

    def __repr__(self):
        s = "Flac file: %s - %s (%s / %d)\n" % (self.artist, self.album,
                                                self.date, self.length)
        s += self.tracks.__str__()
        return s

    def extractThumbnail(self, path):
        # if we've already extracted a thumbnail, return its filename
        if self.coverart and os.path.isfile(self.coverart):
            return self.coverart
        
        # create the output path if it doesn't exist
        if not os.path.isdir(path):
            try:
                os.makedirs(path)
            except:
                print "Can't create path %s" % path
                return None

        os.chdir(path)
        fd, self.coverart = tempfile.mkstemp('.jpg', "thumb", path)
        os.close(fd) # Race condition, I know, big deal.
        cmd = 'metaflac --export-picture-to=%s %s' % \
            (self.coverart, shellquote(self.filename))
        os.system(cmd)
        return self.coverart
    
class FlacLibrary:
    """
    A class representing a complete FLAC library, which is mostly a
    dictionary mapping md5 keys to FlacFile class instances.
    """
    
    def __init__(self, startpath):
        self.rootpaths = [startpath]
        self.flacs = { }
        self.statusnotify = lambda s: sys.stdout.write(s + '\n')
        
    def addpath(self, newpath):
        self.rootpaths.append(newpath)

    def clearpaths(self):
        self.rootpaths = []
        
    def scan(self):
        # clear a flag in each flac entry, so that we can iterate them
        # after we are done scanning and identify any that were not
        # hit (mark and sweep)
        for flac in self.flacs.values():
            flac.verified = False
        # scan each of our possibly many root paths
        for path in self.rootpaths:
            self._scanpath(path)
        # delete any entries that didn't turn up in the scan
        for k in self.flacs.keys():
            if not self.flacs[k].verified:
                del self.flacs[k]
            else:
                del self.flacs[k].verified
        self.statusnotify("Done (%d FLAC files found)." % \
                              len(self.flacs.keys()))
                
    def _scanpath(self, path):
      """
      scanpath() is for the recursive use of scan(), and not really meant
      to be called from the outside.
      """
      try:
        for f in os.listdir(path):
          fname = path.encode() + os.sep + f
          if os.path.isfile(fname) and f.endswith(".flac"):
            count = len(self.flacs.keys())
            if count % 10 == 0:
              self.statusnotify("Searching %s (%d FLAC files found)" \
                                    % (path, count))
            flac = FlacFile(fname)
            if flac.md5:
              if self.flacs.has_key(flac.md5):
                del self.flacs[flac.md5]
              self.flacs[flac.md5] = flac
              self.flacs[flac.md5].verified = True
            else:
              self.statusnotify("Invalid flac file: %s" % f)
          elif (os.path.isdir(fname) and not (fname.startswith("."))):
            self._scanpath(fname)
      except OSError:
        return


def shellquote(s):
    """
    Makes an arbitrary string (hopefully) shell-safe to be given as an
    argument: escapes ", $, and \ characters, then encloses the whole thing
    in " characters.
    """
    ### testing: did I really not know that ' is different from "?
    return "$'%s'" % s.replace("'", r"\'")
    ###
    if not s: return '""'
    s = s.replace('\\', r'\\') # keep this first, or you will make $ into \\$
    s = s.replace(r'"', r'\"')
    s = s.replace(r'$', r'\$')
    s = s.replace(r'&', r'\&')
    return '"' + s + '"'

def filequote(s):
    """
    Deletes or substitutes the characters that are likely to cause
    non-portable filenames: anything Unicode, and (? * : / \ #).
    """
    if not s: return '""'
    s = s.encode('ascii', 'replace')
    s = s.replace('?', '')
    s = s.replace('*', '')
    s = s.replace(':', '-')
    s = s.replace('/', '-')
    s = s.replace('\\', '-')
    s = s.replace('#', '_')
    return s

def check_binary(cmd, regex):
    """
    given a command and an expected output, tests whether the command can be
    executed by e.g. os.system(), and whether the output matches the expected
    regex.  For example, one might want to test whether 'gcc --version' can be
    executed and whether it returns 'gcc (GCC) 4\.\d+\.\d+'
    """
    out = os.popen4(cmd, "r")[1]
    s = out.read()
    out.close()
    m = re.findall(regex, s)
    # this looks useless, but we want to explicitly return a True or
    # False value so that operators like &= will work in calling code
    return not not m

def flacpipe(f, n):
    """
    Assembles a command line that will extract track n from file f
    to standard output.
    """
    cmd = "flac -s -d -c --cue=" + str(n) + ".1-" + str(n + 1) + ".1 "
    cmd += shellquote(f)
    return cmd


def loadSavefile(f):
    """
    Our 'save file' is a list of FlacFile objects and a couple other things,
    pickled in the order defined here.
    """
    fd = open(os.path.expanduser(f), 'r')
    flacs = pickle.load(fd)
    rootpaths = pickle.load(fd)
    outpath = pickle.load(fd)
    return flacs, rootpaths, outpath


def writeSavefile(f, flacs, rootpaths, outpath):
   """see loadSavefile()."""
   fd = open(os.path.expanduser(f), 'w')
   pickle.dump(flacs, fd, pickle.HIGHEST_PROTOCOL)
   pickle.dump(rootpaths, fd, pickle.HIGHEST_PROTOCOL)
   pickle.dump(outpath, fd, pickle.HIGHEST_PROTOCOL)
   fd.close()


if __name__ == '__main__':
    # self-test: Invoke with a path, see all the flacs parsed.
    lib = FlacLibrary(sys.argv[1])
    lib.scan()
    print lib.flacs
    

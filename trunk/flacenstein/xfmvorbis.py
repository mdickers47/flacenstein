"""
Ogg Vorbis (.ogg) transform module for flacenstein.  This relies
on oggenc which is pretty easy to get, Ogg having been developed
specifically to be an unencumbered alternative to e.g. mp3.
Debian package is vorbis-tools.
"""

import os
import re
import sys

import flaclib

description = "Encode to Ogg Vorbis"
status = "init"
notify = lambda s: sys.stdout.write(s + '\n')
outpath = "/tmp/flac"
extension = "ogg"
debug = True

BIN_OGG = "oggenc"
BIN_FLAC = "flac"

def ready():
    """Check whether binaries we need can be executed."""
    status = True
    status &= _check_binary("%s -h" % BIN_OGG, "Usage: oggenc")
    status &= _check_binary("%s -v" % BIN_FLAC, "flac ([0-9\.]+)")
    return status

def encodeFile(job):
    
    # create output directory if necessary
    (outdir, outfile) = os.path.split(job.outfile)
    if not os.path.isdir(outdir):
        try:
            os.makedirs(outdir)
        except:
            notify("Can't create path %s" % outdir)
            os._exit(1)

    cmd = flaclib.flacpipe(job.flacfile, job.tracknum) + " | "
    cmd += "oggenc -o " + flaclib.shellquote(job.outfile)
    cmd += " -a " + flaclib.shellquote(job.artist)
    cmd += " -l " + flaclib.shellquote(job.album)
    cmd += " -t " + flaclib.shellquote(job.title)
    cmd += " -N " + str(job.tracknum)
    cmd += " -"
    if debug: print "Executing:", cmd
    os._exit(os.system(cmd))

def cleanup():
    """this module doesn't use any temp files, so nothing to do here"""
    pass

def _check_binary(cmd, regex):
    out = os.popen4(cmd, "r")[1]
    s = out.read()
    out.close()
    m = re.findall(regex, s)
    if not m:
        _setstatus("Can't execute command %s" % cmd)
        return False
    return True

def _setstatus(msg):
    global status
    notify(msg)
    status = msg
    
if __name__ == '__main__':
    print "Testing '%s' module..." % description
    if ready():
        print "Self tests ok."
    else:
        print "Self tests failed!"
    

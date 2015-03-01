"""
Ogg Vorbis (.ogg) transform module for flacenstein.  This relies
on oggenc which is pretty easy to get, Ogg having been developed
specifically to be an unencumbered alternative to e.g. mp3.
Debian package is vorbis-tools.
"""

import os
import re
import subprocess
import sys

import flaccfg
import flaclib

description = "Encode to Ogg Vorbis"
status = "init"
notify = lambda s: sys.stdout.write(s + '\n')
outpath = "/tmp/flac"
extension = "ogg"
debug = True

def ready():
    """Check whether binaries we need can be executed."""
    ok = True
    ok &= flaclib.check_binary([flaccfg.BIN_OGG, '-h'],
                               'Usage: oggenc',
                               loud=True)
    ok &= flaclib.check_binary([flaccfg.BIN_FLAC, '-v'],
                               r'flac ([0-9\.]+)',
                               loud=True)
    return ok

def encodeFile(job):
    
    # create output directory if necessary
    (outdir, outfile) = os.path.split(job.outfile)
    if not os.path.isdir(outdir):
        try:
            os.makedirs(outdir)
        except:
            notify("Can't create path %s" % outdir)
            os._exit(1)

    cmd = [flaccfg.BIN_OGG, '-o', job.outfile,
           '-a', job.artist,
           '-l', job.album,
           '-t', job.title,
           '-N', str(job.tracknum),
           '-']
    flac_stdout = flaclib.flacpipe(job.flacfile, job.tracknum)
    ogg_child = subprocess.Popen(cmd, stdin=flac_stdout)
    flac_stdout.close()
    ogg_child.wait()
    os._exit(ogg_child.returncode)

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
    

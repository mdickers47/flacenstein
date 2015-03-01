"""
AAC (MPEG4, .m4a) transform module for flac library program.  This
relies on FAAC which is somewhat hard to get, no doubt because it
violates any number of Quicktime licenses or patents, which MPEG-4 is
based on.  faac is at http://audiocoding.com, with Debian packages at
http://www.rarewares.org/.
"""

import os
import subprocess
import sys

import flaclib
import flaccfg

# The following are required for all transform modules, and will be
# used by Flacenstein.
description = "Encode to MPEG4/AAC"
status = "init"
notify = lambda s: sys.stdout.write(s + '\n')
outpath = "/tmp/flac"
extension = "m4a"

artdir = ""

def ready():
    """
    The ready() method checks that all the binaries this module requires
    can be executed, and returns True if they can.
    """
    ok = True
    ok &= flaclib.check_binary(['faac'], 
                               r'FAAC [0-9\.]+',
                               loud=True)
    ok &= flaclib.check_binary([flaccfg.BIN_FLAC, '-v'],
                               r'flac [0-9\.]+',
                               loud=True)
    return ok

def encodeFile(job):

    # create output directory if necessary
    (outdir, outfile) = os.path.split(job.outfile)
    if not os.path.isdir(outdir):
        try:
            os.makedirs(outdir)
        except:
            print "Can't create path", outdir
            os._exit(1)
        
    # Beware, untested!
    cmd = ['faac', '-o', job.outfile,
           '--artist', job.artist,
           '--album', job.album,
           '--title', job.title,
           '--track', str(job.tracknum)]
    if job.coverart:
        cmd.extend(['--cover-art', job.coverart])
    cmd.append('-')
    flac_stdout = flaclib.flacpipe(job.flacfile, job.tracknum)
    faac_child = subprocess.Popen(cmd, stdin=flac_stdout)
    flac_stdout.close()
    faac_child.wait()
    os._exit(faac_child.returncode)

def cleanup():
    """We can at least try to clean up after ourselves, if the caller calls
    cleanup() after finishing with the processFlac()s."""
    global artdir
    if os.path.isdir(artdir):
        os.rmdir(artdir)
        artdir = ""
        
            
def _setstatus(msg):
    global status
    notify(msg)
    status = msg
    
if __name__ == '__main__':
    print "Testing", description, "module..."
    if ready():
        print "Self tests ok."
    else:
        print "Self tests failed!"

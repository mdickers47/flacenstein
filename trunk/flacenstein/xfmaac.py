"""
AAC (MPEG4, .m4a) transform module for flac library program.  This
relies on FAAC which is somewhat hard to get, no doubt because it
violates any number of Quicktime licenses or patents, which MPEG-4 is
based on.  faac is at http://audiocoding.com, with Debian packages at
http://www.rarewares.org/.
"""

import os
import re
import sys

import flaclib

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
    out = os.popen4("faac", "r")[1]
    s = out.read()
    out.close()
    if not re.compile("FAAC [0-9\.]+").search(s):
        _setstatus("Can't execute faac program.")
        return False
    out = os.popen4("flac -v", "r")[1]
    s = out.read()
    out.close()
    if not re.compile("flac [0-9\.]+").search(s):
        _setstatus("Can't execute flac program.")
        return False
    return True

def encodeFile(job):

    # create output directory if necessary
    (outdir, outfile) = os.path.split(job.outfile)
    if not os.path.isdir(outdir):
        try:
            os.makedirs(outdir)
        except:
            print "Can't create path", outdir
            os._exit(1)
        
    # prepare complicated pipeline command that will turn the flac track
    # into an .m4a file
    cmd = flaclib.flacpipe(job.flacfile, job.tracknum) + " | "
    cmd += "faac -o "   + flaclib.shellquote(job.outfile)
    cmd += " --artist " + flaclib.shellquote(job.artist)
    cmd += " --album "  + flaclib.shellquote(job.album)
    cmd += " --title "  + flaclib.shellquote(job.title)
    cmd += " --track "  + str(job.tracknum)
    if (job.coverart):
        cmd += " --cover-art " + flaclib.shellquote(job.coverart)
    cmd += " - " # 2>/dev/null"
    #notify("Executing: %s" % cmd)
    #os._exit(os.system(cmd))
    print 'Executing: ', cmd
    #os.execv('/bin/sh', ['-c', cmd])
    ret = os.system(cmd)
    sys.exit(ret)
    # note we never return, we exit

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

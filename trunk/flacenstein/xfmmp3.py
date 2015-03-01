"""
MP3 transform module for flacenstein.  This relies on lame which
is sort of hard to get; Debian packages can be found at rarewares.org
like FAAC.
"""

import os
import sys

import flaclib
import flaccfg

description = "Encode to MP3"
status = "init"
notify = lambda s: sys.stdout.write(s + '\n')
outpath = "/tmp/flac"
extension = "mp3"
debug = True

def ready():
    """
    Check whether binaries we need can be executed.
    """
    ok = True
    ok &= flaclib.check_binary([flaccfg.BIN_LAME, '--version'],
                               "LAME (\d\dbits )?version ([0-9\.]+)",
                               loud=True)
    ok &= flaclib.check_binary([flaccfg.BIN_FLAC, '-v'],
                               "flac ([0-9\.]+)",
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

    cmd = flaclib.flacpipe(job.flacfile, job.tracknum) + " | "
    cmd += "lame --preset standard"
    cmd += " --ta " + flaclib.shellquote(job.artist)
    cmd += " --tl " + flaclib.shellquote(job.album)
    cmd += " --tt " + flaclib.shellquote(job.title)
    cmd += " --tn " + str(job.tracknum)
    cmd += " - " + flaclib.shellquote(job.outfile)
    if debug: print "Executing:", cmd
    os._exit(os.system(cmd))

def cleanup():
    """this module doesn't use any temp files, so nothing to do here"""
    pass

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
    

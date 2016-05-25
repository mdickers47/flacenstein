"""
Opus transform module for flacenstein.  Requires opus-tools.
"""

import os
import subprocess
import sys

import flaclib
import flaccfg

description = "Encode to Opus"
status = "init"
notify = lambda s: sys.stdout.write(s + '\n')
outpath = "/tmp/flac"
extension = "opus"
debug = True

def ready():
    """
    Check whether binaries we need can be executed.
    """
    ok = True
    ok &= flaclib.check_binary([flaccfg.BIN_OPUS, '--version'],
                               "opusenc opus-tools",
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

    cmd = ['opusenc', # accept default bitrate of 96kbps per stereo pair
           '--quiet',
           '--artist', job.artist,
           '--album', job.album,
           '--title', job.title,
           '--comment', 'TRACKNUMBER=%s' % str(job.tracknum)]
    if job.coverart: cmd.extend(['--picture', job.coverart])
    cmd.extend(['-', job.outfile])
    flac_stdout = flaclib.flacpipe(job.flacfile, job.tracknum)
    opus_child = subprocess.Popen(cmd, stdin=flac_stdout)
    flac_stdout.close() # recall it's been duplicated into the lame process
    opus_child.wait()
    os._exit(opus_child.returncode)

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
    

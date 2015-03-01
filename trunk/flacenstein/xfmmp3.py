"""
MP3 transform module for flacenstein.  This relies on lame which
seems to no longer be hard to get; ubuntu 14.10 can just do
'apt-get install lame' from the normal sources.
"""

import os
import subprocess
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

    cmd = [flaccfg.BIN_LAME, '--preset', 'standard',
           '--ta', job.artist,
           '--tl', job.album,
           '--tt', job.title,
           '--tn', str(job.tracknum)]
    if job.coverart:
        cmd.extend(['--ti', job.coverart])
    cmd.extend(['-', job.outfile])
    flac_stdout = flaclib.flacpipe(job.flacfile, job.tracknum)
    lame_child = subprocess.Popen(cmd, stdin=flac_stdout)
    flac_stdout.close() # recall it's been duplicated into the lame process
    lame_child.wait()
    os._exit(lame_child.returncode)

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
    

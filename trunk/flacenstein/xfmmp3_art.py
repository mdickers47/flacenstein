"""
MP3 transform module for flacenstein, modified to do tag insertion via
pyid3lib rather than relying on lame.  There is one advantage to doing
this, which is that we can support cover art.  But it is a separate
module so that mp3 encoding will still be possible when pyid3lib
inevitably dies or mutates or becomes unavailable.

This still depends on lame, of course.
"""

import os
import pyid3lib
import sys

import flaclib
import flaccfg

description = "Encode to MP3 with cover art"
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
    ok &= flaclib.check_binary("%s --version" % flaccfg.BIN_LAME,
                               "LAME (\d\dbits )?version ([0-9\.]+)")
    ok &= flaclib.check_binary("%s -v" % flaccfg.BIN_FLAC, 
                               "flac ([0-9\.]+)")
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

    cmd = flaclib.flacpipe(job.flacfile, job.tracknum) \
        + ' | lame --preset medium - ' + flaclib.shellquote(job.outfile)
    if debug: print "Executing:", cmd
    ret = os.system(cmd)

    # hack up tags post-lame
    if debug: print 'Setting id3 tags: artist "%s" title "%s"' % \
            (job.artist, job.title)
    tag = pyid3lib.tag(job.outfile)
    # No idea wtf type has ended up in these strings, but pyid3lib craps out
    # without the str().  Probably has to do with more unicode bullshit.
    tag.artist = str(job.artist)
    tag.album = str(job.album)
    tag.title = str(job.title)
    tag.track = job.tracknum
    if job.coverart:
        # following example at: http://pyid3lib.sourceforge.net/doc.html
        mimetype = 'image/jpeg'
        if job.coverart.endswith('png'): mimetype = 'image/png'
        d = { 'frameid': 'APIC',
              'mimetype': mimetype,
              'description': 'Cover art',
              'picturetype': 3,
              'data': open(job.coverart, 'rb').read() }
        tag.append(d)
        if debug: print 'Added covert art tag %s mime type %s' % \
                (job.coverart, mimetype)
    tag.update()

    os._exit(ret)

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
    

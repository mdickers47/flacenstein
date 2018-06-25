#!/usr/bin/python -u

import os
import re
import sys
import urllib


PATH_HACKS = { '/c/media/' : '/Volumes/media/' }

def secs_to_samples(secs):
    return int(secs * 44100)

def decode_flac(fname, start, end, num):
    cmd = 'flac -d -o track%02d.wav ' % num
    cmd += '--skip=%d ' % start
    cmd += '--until=%d ' % end
    cmd += '"' + fname + '"'
    print 'Excecuting %s' % cmd
    if os.system(cmd) != 0: raise Exception('flac crashed')
    
    
def decode_mp3(fname, num):
    #cmd = 'mpg123 --wav track%02d.wav ' % num
    #cmd += '"' + fname + '"'
    cmd = "mplayer -ao pcm $'%s' && mv audiodump.wav track%02d.wav" % \
	  (fname.replace("'", "''"), num)
    print 'Executing %s' % cmd
    if os.system(cmd) != 0: raise Exception('mp3 crashed')

pl = open(sys.argv[1], 'r')
cue = open('audiocd.cue', 'w')
tracknum = 1

# throw first line away, which appears to contain binary squeezebox magic
l = pl.readline()

while True:
    l = pl.readline()
    if len(l) <= 1: break
    if l.startswith('#'): continue
    if l.endswith('\n'): l = l[:-1]
    for key, val in PATH_HACKS.items(): l = l.replace(key, val)
    m = re.match('file://([^#]+)#?([\d\.]+)?\-?([\d\.]+)?', l)
    if m:
        fname = urllib.unquote(m.group(1))
        start = secs_to_samples(float(m.group(2)))
        end   = secs_to_samples(float(m.group(3)))
        print 'File %s, from %s to %s' % (fname, start, end)
        decode_flac(fname, start, end, tracknum)
    else:
        print 'File %s' % l
        decode_mp3(l, tracknum)
    cue.write('FILE "track%02d.wav" WAVE\n' % tracknum)
    cue.write('TRACK %02d AUDIO\n'% tracknum)
    cue.write('INDEX 01 00:00:00\n')
    tracknum += 1
        
pl.close()
cue.close()

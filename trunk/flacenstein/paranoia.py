"""Not really a Python wrapper to libparanoia, although that would be cool.
This is just a few things that I need to recreate the cdparanoia progress bar
using the status information dumped to stderr by -e."""

import string

# constants from paranoia/cdda_paranoia.h

CD_FRAMESIZE_RAW = 2352
CD_FRAMEWORDS    = CD_FRAMESIZE_RAW / 2

# status message constants from paranoia/cdda_paranoia.h

PARANOIA_CB_READ          = 0
PARANOIA_CB_VERIFY        = 1
PARANOIA_CB_FIXUP_EDGE    = 2
PARANOIA_CB_FIXUP_ATOM    = 3
PARANOIA_CB_SCRATCH       = 4
PARANOIA_CB_REPAIR        = 5
PARANOIA_CB_SKIP          = 6
PARANOIA_CB_DRIFT         = 7
PARANOIA_CB_BACKOFF       = 8
PARANOIA_CB_OVERLAP       = 9
PARANOIA_CB_FIXUP_DROPPED = 10
PARANOIA_CB_FIXUP_DUPED   = 11
PARANOIA_CB_READERR       = 12

pbarlength  = 30
progressbar = [" " for i in range(0,pbarlength)]
startsector = 0
sectorlen   = 0
readsector  = 0

def setupStatus(start, end):
    """we need to know the start and end sectors for the job in order to
    translate sector numbers into progress bar positions"""
    global startsector, sectorlen, readsector, progressbar
    startsector = start
    sectorlen = end - start
    readsector = start
    progressbar = [" " for i in range(0,30)]
    return

def updateStatus(msg, inpos):
    """a crude imitation of callback() in main.c"""
    sector = inpos / CD_FRAMEWORDS
    pos = int((float(sector - startsector) / sectorlen) * pbarlength)
    if pos < 0 or pos > pbarlength - 1:
        print "position out of bounds: %d (%d of %d+%d)" \
              % (pos, sector, startsector, sectorlen)
        return
    
    cur = progressbar[pos]
    if msg == PARANOIA_CB_VERIFY:
        pass
    elif msg == PARANOIA_CB_READ:
        global readsector
        if sector > readsector:
            readsector = sector
    elif msg == PARANOIA_CB_FIXUP_EDGE:
        if cur == ' ':
            cur == '-'
    elif msg == PARANOIA_CB_FIXUP_ATOM:
        if cur == ' ' or cur == '-':
            cur = '+'
    elif msg == PARANOIA_CB_READERR:
        if cur != 'V':
            cur = 'e'
    elif msg == PARANOIA_CB_SKIP:
        cur = 'V'
    elif msg == PARANOIA_CB_FIXUP_DROPPED or msg == PARANOIA_CB_FIXUP_DUPED:
        if cur == ' ' or cur == '-' or cur == '+':
            cur = '!'
    progressbar[pos] = cur

def getStatus():
    """hack in the > character for display, just like the real cdparanoia"""
    p = progressbar[:]
    readpos = int((float(readsector - startsector) / sectorlen) * pbarlength)
    if readpos >= 0 and readpos < pbarlength:
        p[readpos] = '>'
    p.insert(0, '[')
    p.insert(len(p), ']')
    return string.join(p, '')

def getFinalStatus():
    """return just the status icons without the > progress indicator"""
    p = progressbar[:]
    p.insert(0, '[')
    p.insert(len(p), ']')
    return string.join(p, '')

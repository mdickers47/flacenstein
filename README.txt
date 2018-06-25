Here lies 20 years of homemade tools meant to future-proof a large
number of CDs using the lossless FLAC format.  It is all organized
around the concept of one file per CD.  These files contain the
following FLAC metadata blocks:

+ CUESHEET, to identify where to cut up the stream into tracks.  It is
  approximately the TOC from the original CD, except some oddities
  about lead-in and lead-out have to be sanded off.

+ VORBIS_COMMENT which contains at least ARTIST, ALBUM, DATE, and an
  array of TITLE tags.

+ PICTURE with, hopefully, a jpeg of the cover art.

The above have all been incorporated into the FLAC standard since
2006, and there has been no need to touch the master file format in 12
years.

However, there is still no generally agreed "standard" for files
containing compound streams.  This means that even players and tools
that claim "FLAC support," of which there are now a lot, almost always
think each file is one hour-long track.  So it goes.  For a decade I
maintained a set of patches to the slimserver, which allowed it to see
inside the compound files.  The functionality was eventually adopted
upstream.  But the slimserver got steadily more bloated and
unreliable.  Then Slim Devices was bought by Logitech, the server was
renamed "Logitech Media Server," and the bloating accelerated.  Now
the whole product line is dead.  So it goes.

Now I don't try to get compound FLAC files to be understood by
anything.  I just spend a couple of CPU-months to transcode the entire
hierarchy into each new flavor of compressed file when it comes along
(which these tools can do).  The 2018 best flavor is opus.

Contents:

flac-image

   Prior to release 1.1.3 in 2006, FLAC had no standardized metadata
   block to store cover art.  But when iPods gained color displays
   everybody had to have it.  This was my own scheme for stuffing an
   arbitrary binary blob into a metadata block, identified by
   mime-type.  Its metadata ID 0x696d6167 (ASCII "imag") is registered
   with FLAC (see https://xiph.org/flac/id.html).  After 2006, there
   was no more need for a custom metadata block, so I converted all my
   files and stopped using flac-image.

   flac-image is written in C and needs to link against the reference
   FLAC library.

flac-gui

   Maintained until 2015, then abandoned in the face of yet another
   pointless rewrite forced by mutation in the wxwidgets libraries.
   Does not run today and is unlikely to be fixed by me.

   At different points in time flac-gui worked with cddb for automatic
   identification of discs, then MusicBrainz when that was the fashion
   for five seconds, and even an Amazon API for automatic retrieval of
   cover art.  None of these fancy features ever had a half-life
   greater than about 6 months before the service would make a
   breaking change.  Likewise for about five CADT generations of
   Python FLAC access libraries.  Likewise for the furiously developed
   wxwidgets libraries.

   Thus over time all the external dependencies were replaced with
   "os.system" or dropped, and now, all round that decay, the lone
   and level sands stretch far away.
   
flac-cli

   Was actively maintained until at least 2018, and is probably in
   working condition.  Can be run right where it is with 'python[2.7]
   flac-cli.py'.  Contains all the functionality of the GUI version
   except to rip a new CD.  For that I now just use util/rip.sh, which
   does the same thing with 1% of the complexity.

utils

   A bunch of hacky scripts.  Mostly bash and mostly run on their own
   with no dependencies except the flac and metaflac binaries.  Some
   like flactags.sh are generally useful to have in $PATH.  Others
   were written to work out a one-time problem that will probably
   never happen again.

--

25 Jun 2018 Mikey Dickerson

#!/usr/bin/python
"""
A hack to convert a collection of FLAC files in the style of www.etree.org
into a single file with cuesheet and tags, in the style of flacenstein.

This is probably going to end up being a tour of pyflac: we need to find
the stream lengths from the metadata, decode the streams, re-encode them
in one long stream, and construct a cuesheet in the new file.

Copyright (c) 2005 Michael A. Dickerson.  Modification and redistribution
are permitted under the terms of the GNU General Public License, version 2.
"""

import os
import sys
import wave
import flac.metadata as md
import flac.encoder as enc
import flac.decoder as dec

from flacenstein import flaccfg

CD_SAMPLES_PER_FRAME = 588 # 44100 samples/sec / 75 frames/sec
SECONDS_PER_SEEKPOINT = 10.031 # magic number? observed to be what flac does
FLAC_BLOCK_SIZE = 4608 # another magic number observed from flac

samples_decoded = 0
samples_encoded = 0

class outstream:

    def __init__(self):
        self.sample_rate = None
        self.channels = None
        self.bits_per_sample = None
        self.blocksize = None
        self.total_samples = 0 # accumulated stream length, in samples
        self.filename = 'combined.flac' # TO DO: be less lame
        self.encoder = None
        self.track_offsets = []
        self.track_count = 0
        self.last_progress = None
        self.bufsize = 2048
        
    def start_track(self):
        offset = self.total_samples
        if offset % CD_SAMPLES_PER_FRAME:
            print 'WARNING: track boundary not aligned to frame boundary; will be rounded'
        print 'Track starts at %d samples (%d sec)' \
              % (offset, offset / self.sample_rate)
        self.track_offsets.append(offset)

    def init(self):
        if self.encoder == None:
            self.encoder = enc.FileEncoder()
            print "Opening output stream: %s" % self.filename
            self.encoder.set_filename(self.filename)
            print "Setting channels to %d" % self.channels
            self.encoder.set_channels(self.channels)
            print "Setting sample bit depth to %d" % self.bits_per_sample
            self.encoder.set_bits_per_sample(self.bits_per_sample)
            print "Setting sample rate to %d" % self.sample_rate
            self.encoder.set_sample_rate(self.sample_rate)
            print "Setting progress callback"
            self.encoder.set_progress_callback(handle_encoder_progress)
            if self.blocksize == None: self.blocksize = FLAC_BLOCK_SIZE
            print "Setting block size to %d" % self.blocksize
            self.encoder.set_blocksize(self.blocksize)
            print "Setting mid/side stereo encoding"
            self.encoder.set_do_mid_side_stereo(True)
            ## 27 Nov 05 MAD: None of this works; I think pyflac doesn't have
            ## all the bindings it needs, or if it does, I can't figure out how to use it.
            ##
            # we don't know any metadata to create a priori, but leave
            # space for it
            #print "Creating padding block"
            #pad = md.Padding()
            #print "Setting padding length to 128k"
            #pad.set_length(256 * 1024)
            #print "Attaching padding block to output stream"
            #self.encoder.set_metadata((pad.block(),), 1)
            #print "Creating seektable"
            #tbl = md.SeekTable()
            #tbl.template_append_spaced_points(100, nsamples) # nsamples is bullshit
            #tbl.template_sort(True)
            #print "Creating VORBIS block"
            #vorbis = md.VorbisComment()
            #vorbis.comments['ARTIST'] = 'fixme'
            #print "Sending metadata blocks to output stream"
            #self.encoder.set_metadata((tbl.block, vorbis.block), 2)
            print "Initializing encoder"
            if self.encoder.init() != enc.FLAC__FILE_ENCODER_OK:
                print "ERROR: encoder.init() failed"
                sys.exit(1)
            else:
                print "encoder is ready"
                
    def set_channels(self, n):
        if self.channels == None or self.channels == n:
            self.channels = n
        else:
            raise 'Number of channels changed from %d to %d' % (self.channels, n)

    def set_sample_rate(self, n):
        if self.sample_rate == None or self.sample_rate == n:
            self.sample_rate = n
        else:
            raise 'Sample rate changed from %d to %d' % (self.sample_rate, n)

    def set_bits_per_sample(self, n):
        if self.bits_per_sample == None or self.bits_per_sample == n:
            self.bits_per_sample = n
        else:
            raise 'Bit depth changed from %d to %d' % (self.bits_per_sample, n)

    def set_block_size(self, n):
        if self.block_size == None: self.block_size = n
        
    def process(self, data, nbytes):
        """
        WATCH VERY CAREFULLY!  The decoder callback gets called with a buffer and
        a number indicating how many BYTES in the buffer.  But the encoder
        function needs to be given a buffer and the number of SAMPLES in the buffer.
        We have to convert by the correct number of bytes-per-channel-per-sample.
        Without converting, we either seg fault or corrupt the output stream beyond
        all recognition.
        
        We won't talk about how long it took me to figure this out.
        """
        nsamples = nbytes * 8 / self.bits_per_sample / self.channels
        self.process_samples(data, nsamples)

    def process_samples(self, data, nsamples):
        """
        Although if you are using the wave module to read straight PCM data,
        then you already know how many samples.
        """
        self.encoder.process(data, nsamples)
        self.total_samples += nsamples

    def finish(self):
        # NB: If the total number of samples encoded is not a multiple of 588
        # (CD frame size), then the Perl cuesheet parser in the slimserver will
        # barf and you will see this flac as one long track.  It is hard not to
        # see this as a bug, since there is no actual reason to enter the very
        # end of the stream in the TOC, cuesheet, or seek table.
        if (self.total_samples % CD_SAMPLES_PER_FRAME):
            padding = CD_SAMPLES_PER_FRAME - (self.total_samples % CD_SAMPLES_PER_FRAME)
            print 'Padding end of stream with %d samples' % padding
            bytes = padding * (self.bits_per_sample / 8) * self.channels
            self.process_samples('\0' * bytes, padding)
        
        self.encoder.finish()
        self.encoder = None
        # TO DO: it appears that pyflac can't construct or modify cuesheet
        # blocks?  or at least the bindings don't match the C documentation?
        print 'Creating padding...',
        os.system('%s --add-padding=%d %s' % (flaccfg.BIN_METAFLAC, 128*1024, self.filename))
        print 'done.'
        print 'Creating seek table...',
        os.system('%s --add-seekpoint=%fs %s' % (flaccfg.BIN_METAFLAC, \
                                                 SECONDS_PER_SEEKPOINT, self.filename))
        print 'done.'
        print 'Writing cuesheet...',
        cue = os.popen('%s --import-cuesheet-from=- %s' % (flaccfg.BIN_METAFLAC, \
                                                           self.filename), 'w')
        cue.write('FILE "dummy.wav" WAVE\n')
        for i in range(0, len(self.track_offsets)):
            cue.write('  TRACK %02d AUDIO\n' % (i + 1))
            frames = self.track_offsets[i] / CD_SAMPLES_PER_FRAME
            # note: if self.track_offsets[i] was not a multiple of 588, we just
            # introduced a small rounding error
            (secs, frames) = divmod(frames, 75)
            (mins, secs) = divmod(secs, 60)
            cue.write('    INDEX 01 %02d:%02d:%02d\n' % (mins, secs, frames))
        cue.close()
        print 'done.'
        
def handle_encoder_progress(encoder, bytes, samples, frames, total_frames_est):
    #print "in handle_encoder_progress"
    global samples_encoded
    samples_encoded = samples
    sys.stdout.write('\b' * 22)
    sys.stdout.write('%6d frames complete' % frames)
    sys.stdout.flush()
            
def handle_decoder_metadata(decoder, block):
    global out
    if block.type == md.STREAMINFO:
        info = block.data.stream_info
        out.set_sample_rate(info.sample_rate)
        out.set_channels(info.channels)
        out.set_bits_per_sample(info.bits_per_sample)
        out.blocksize == info.max_blocksize
        out.start_track()

def handle_decoder_write(decoder, buf, size):
    global out
    global samples_decoded
    #print "called decoder_write with %d bytes at %d" % (size, decoder.get_decode_position())
    samples = size * 8 / out.bits_per_sample / out.channels
    samples_decoded += samples
    if size != len(buf):
        print "ERROR: size %d does not match len(buf) %d" % (size, len(buf))
        sys.exit(1)
    if out.process(buf, size) != enc.FLAC__FILE_ENCODER_OK:
        return dec.FLAC__FILE_DECODER_OK
    else:
        print "WARNING: encoder signalled status %d" % out.encoder.get_state()

def handle_decoder_error(decoder, status):
    print "ERROR: decoder signalled status %d" % status
    
# ------- work starts here -------

tracklist = open(sys.argv[1], 'r')
out = outstream()

infile = tracklist.readline()[:-1]
while (infile):
    print "-----> Reading file: %s" % infile
    if infile.endswith('flac'):
        
        decoder = dec.FileDecoder()
        decoder.set_filename(infile)
        decoder.set_metadata_respond_all()
        decoder.set_write_callback(handle_decoder_write)
        decoder.set_metadata_callback(handle_decoder_metadata)
        decoder.set_error_callback(handle_decoder_error)
        # off we go
        decoder.init()
        decoder.process_until_end_of_metadata()
        out.init()
        decoder.process_until_end_of_file()
        decoder.finish()
        
    elif infile.endswith('wav'):
        
        bufsize = 1024
        wav = wave.open(infile, 'r')
        out.set_channels(wav.getnchannels())
        out.set_bits_per_sample(wav.getsampwidth() * 8)
        out.set_sample_rate(wav.getframerate())
        out.start_track()
        out.init()
        
        data = wav.readframes(bufsize)
        while data:
            out.process_samples(data, bufsize)
            data = wav.readframes(bufsize)
        wav.close()

    else:
        print "skipping: name ends with neither flac nor wav"
        
    infile = tracklist.readline()[:-1]
    
out.finish()
print '%d samples decoded' % samples_decoded
print '%d samples encoded' % samples_encoded

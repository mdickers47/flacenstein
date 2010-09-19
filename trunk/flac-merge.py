#!/usr/bin/python
"""
flac-merge.py - Concatenate many flac files into one.

The specified files are combined in the order given on the command
line.  The output flac file is tagged with the first artist that was
found, the first album, and one TITLE tag from each input file.  A
cuesheet is constructed, where each input file is marked as one track.

This mostly makes sense if the input files are tracks from the same
album.

Copyright 2008 Michael A. Dickerson <mikey@singingtree.com>
"""

import os
import sys
import wave

from flacenstein import flaclib

BUFSIZ = 1024 * 1024 # 1M

INTENTIONALLY_BLANK = 'ThIs VaLuE ShOuLd NeVeR OcCuR In NaTuRe!!1'

def _merge_tag(name, val, outflac):
  if name not in outflac.tags or outflac.tags[name] is None:
    outflac.tags[name] = val
  else:
    if val == outflac.tags[name] or outflac.tags[name] is INTENTIONALLY_BLANK:
      return
    else:
      sys.stderr.write('Dropping tag %s which varies between tracks\n' % name)
      # If we do 'del outflac.tags[name]', then the flaclib object
      # will stop understanding name as an attribute--the next
      # outflac.name=x will crash.  If we do outflac.tags[name] =
      # None, the next track to come along will happily set it again.
      # So we have to use a special magic value to indicate 'this
      # space intentionally left blank'.  Sorry.
      outflac.tags[name] = INTENTIONALLY_BLANK


if __name__ == '__main__':

  src_flacs = sys.argv[1:]
  tracknum = pos = 0
  outflac = flaclib.FlacFile(None)
  cuesheet = ['FILE "dummy.wav" WAVE']
  out = None

  for f in src_flacs:
    flac = flaclib.FlacFile(f)
    tracknum += 1

    # Sanity check that you are merging compatible streams.
    if outflac.channels is None:
      outflac.channels = flac.channels
    else: assert outflac.channels == flac.channels
    if outflac.bits_per_sample is None:
      outflac.bits_per_sample = flac.bits_per_sample
    else: assert outflac.bits_per_sample == flac.bits_per_sample
    if outflac.sample_rate is None:
      outflac.sample_rate = flac.sample_rate
    else: assert outflac.sample_rate == flac.sample_rate

    # Merge tags to output flac.  All single-value tags (everything except
    # TRACK) are treated the same.
    for name, val in flac.tags.items(): _merge_tag(name, val, outflac)
    # Even if the input flac contains >1 TITLE tag, we are only going to make
    # one cuesheet entry for it, so we only save the first TITLE.
    if len(flac.tracks) > 0:
      outflac.tracks.append(flac.tracks[0])
    else:
      outflac.tracks.append('Track %s' % tracknum)
    
    # Open output stream after finding first input stream.  Note that we can't
    # quite do this in a single pass, because wave.open() won't write to a pipe.
    if out is None:
      assert not os.path.exists('combined.wav')
      out = wave.open('combined.wav', 'w')
      out.setnchannels(outflac.channels)
      out.setsampwidth(outflac.bits_per_sample / 8)
      out.setframerate(outflac.sample_rate)
      wav_frame_size = outflac.channels * outflac.bits_per_sample/8

    # Create cuesheet entry.  Note that metaflac outputs cuesheets with
    # index points given as 'INDEX 01 12345678', but does not accept this
    # as input.  Yay.
    cuesheet.append('  TRACK %02d AUDIO' % tracknum)
    frames, slop = divmod(pos, flaclib.CD_SAMPLES_PER_FRAME)
    secs, frames = divmod(frames, 75)
    mins, secs = divmod(secs, 60)
    assert slop == 0
    cuesheet.append('    INDEX 01 %02d:%02d:%02d' % (mins, secs, frames))
    print 'Track %d begins at %02d:%02d:%02d' % (tracknum, mins, secs, frames)

    # Beware: when wave talks about "frames" it means single samples,
    # of size (x channels * y bytes per sample).  But our cuesheet may
    # only contain track markers at Red Book/CDDA "frame" boundaries,
    # which means the number of wav-frames must be 0 mod 588.
    print 'Decoding %s, expecting %ld samples' % (f, flac.samples)
    cmd = 'flac -s -d -c %s' % flaclib.shellquote(f)
    wav = wave.open(os.popen(cmd), 'r')
    buf = True
    wav_frames = 0
    while buf:
      buf = wav.readframes(BUFSIZ)
      out.writeframesraw(buf)
      assert len(buf) % wav_frame_size == 0
      wav_frames += len(buf) / wav_frame_size

    assert wav_frames == flac.samples
    pos += flac.samples

    if wav_frames % flaclib.CD_SAMPLES_PER_FRAME:
      # There's no point trying to do anything fancy like insert a wav silence
      # chunk, the output is going to be fed to flac anyway.
      padding_samples = (0 - wav_frames) % flaclib.CD_SAMPLES_PER_FRAME
      print 'Writing %d samples to pad track to CDDA frame boundary' % \
          padding_samples
      padding = '\0' * padding_samples * wav_frame_size
      out.writeframesraw(padding)
      pos += padding_samples

    ret = wav.close()
    if ret:
      print 'fatal: flac returned %s' % ret
      print 'command was: %s' % cmd 
      sys.exit(1)

  out.close()
  outflac.filename = outflac.suggestFilename()
  assert not os.path.exists(outflac.filename)
  print 'Compressing output to %s' % outflac.filename
  cmd = 'flac -o %s combined.wav' % flaclib.shellquote(outflac.filename)
  ret = os.system(cmd)
  if ret:
    print 'fatal: flac returned %s' % ret
    print 'command was: %s' % cmd

  print 'Deleting combined.wav'
  os.unlink('combined.wav')

  print 'Writing tags'
  # Clean up INTENTIONALLY_BLANK tags.
  for name, val in outflac.tags.items():
    if val == INTENTIONALLY_BLANK: outflac.tags[name] = None
  outflac.saveTags()

  print 'Writing cuesheet'
  outflac.saveCuesheet('\n'.join(cuesheet))

#!/usr/bin/python
"""
flac-merge.py - Concatenate many flac files into one.

The specified files are combined in the order given on the command
line.  The output flac file is tagged with the first artist that was
found, the first album, and one TITLE tag from each input file.  A
cuesheet is constructed, where each input file is marked as one track.

This mostly makes sense if the input files are tracks from the same
album.  Or if they're not, but you want to make them into an "album."

Copyright 2008 Mikey Dickerson <mikey@singingtree.com>
"""

import os
import subprocess
import sys
import wave

from flacenstein import flaclib

class Error(Exception): pass
class IncompatibleStreams(Error): pass

BUFSIZ = 1024 * 1024 # 1M

INTENTIONALLY_BLANK = 'ThIs VaLuE ShOuLd NEVeR OccuR In NaTuRe!!1'

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

def _check_metadata(outflac, channels, depth, sample_rate):
  # If this is the first input file, it sets the format of the
  # output.
  if outflac.channels is None: outflac.channels = channels
  if outflac.bits_per_sample is None: outflac.bits_per_sample = depth
  if outflac.sample_rate is None: outflac.sample_rate = sample_rate

  # Otherwise check that you are merging compatible streams.  To live
  # in one happy bitstream all the below must be the same.  If they
  # are not, rewriting the bits to match is out of scope.
  if outflac.channels != channels:
    raise IncompatibleStreams("channel count mismatch")    
  if outflac.bits_per_sample != depth:
    raise IncompatibleStreams("bit depth mismatch")
  if outflac.sample_rate != sample_rate:
    raise IncompatibleStreams("sample rate mismatch")
  
  return True


if __name__ == '__main__':

  src_files = sys.argv[1:]
  tracknum = pos = 0
  outflac = flaclib.FlacFile(None)
  cuesheet = ['FILE "dummy.wav" WAVE']
  out = None

  for f in src_files:

    if f.endswith('.flac'):

      flac = flaclib.FlacFile(f)
      _check_metadata(outflac, flac.channels,
                      flac.bits_per_sample, flac.sample_rate)

      # Merge tags to output flac.  All single-value tags (everything except
      # TRACK) are treated the same.
      for name, val in flac.tags.items(): _merge_tag(name, val, outflac)
      # Even if the input flac contains >1 TITLE tag, we are only going to make
      # one cuesheet entry for it, so we only save the first TITLE.
      if len(flac.tracks) > 0:
        outflac.tracks.append(flac.tracks[0])
      else:
        # Use the filename as TITLE[x] if we have nothing else
        outflac.tracks.append(f)

      cmd = ['flac', '-s', '-d', '-c', f]
      pcm_in = wave.open(subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout)
      print 'Decoding %s, expecting %ld frames' % (f, flac.samples)
      frames_expected = flac.samples

    elif f.endswith('.wav'):

      try:
        pcm_in = wave.open(f, 'r')
      except wave.Error, e:
        print 'Failed to read %s: %s' % (f, e)
        continue

      _check_metadata(outflac, pcm_in.getnchannels(),
                      pcm_in.getsampwidth() * 8, # it returns bytes
                      pcm_in.getframerate())

      # wav files have no tags, so TITLE[x] becomes the filename, which
      # is at least more useful than "Track x"
      outflac.tracks.append(f)
      print 'Reading %s, expecting %ld frames' % (f, pcm_in.getnframes())
      frames_expected = pcm_in.getnframes()

    else:
      print 'skipping file which is neither wav nor flac: %s' % f
      continue
    
    # Open output stream if it doesn't exist yet.  Note that we can't
    # quite do this in a single pass, because wave.open() won't write to a pipe.
    if out is None:
      assert not os.path.exists('combined.wav')
      out = wave.open('combined.wav', 'w')
      out.setnchannels(outflac.channels)
      out.setsampwidth(outflac.bits_per_sample / 8)
      out.setframerate(outflac.sample_rate)
      wav_frame_size = outflac.channels * outflac.bits_per_sample/8

    tracknum += 1

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
    buf = True
    wav_frames = 0
    while buf:
      buf = pcm_in.readframes(BUFSIZ)
      out.writeframesraw(buf)
      assert len(buf) % wav_frame_size == 0
      wav_frames += len(buf) / wav_frame_size

    assert wav_frames == frames_expected
    pos += frames_expected

    if wav_frames % flaclib.CD_SAMPLES_PER_FRAME:
      # There's no point trying to do anything fancy like insert a wav silence
      # chunk, the output is going to be fed to flac anyway.
      padding_samples = (0 - wav_frames) % flaclib.CD_SAMPLES_PER_FRAME
      print 'Writing %d samples to pad track to CDDA frame boundary' % \
          padding_samples
      padding = '\0' * padding_samples * wav_frame_size
      out.writeframesraw(padding)
      pos += padding_samples

    pcm_in.close()
  
  # (end for f in src_files)

  out.close()
  outflac.filename = outflac.suggestFilename()
  assert not os.path.exists(outflac.filename)
  print 'Compressing output to %s' % outflac.filename
  cmd = ['flac', '-o', outflac.filename, 'combined.wav']
  ret = subprocess.call(cmd)
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

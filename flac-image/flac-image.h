/*
 * Data structures for flac-image
 *
 * Copyright (c) 2005 Michael A. Dickerson.  All rights reserved.  Copying, 
 * modification, redistribution, and use are permitted under the terms of a
 * BSD-style license described in the file "COPYING".
 *
 */
 
/* "imag" is 0x696d6167 in ASCII */
#define APPLICATION_ID "imag"
#define ID_BYTES 4

#define IMAGE_HEADER_VERSION 0x0001
#define IMAGE_HEADER_FILENAME_MAXLEN 32
#define IMAGE_HEADER_MIMETYPE_MAXLEN 32

typedef enum {
  OP_UNDEFINED = 0,
  OP_IMPORT,
  OP_EXPORT,
  OP_DELETE,
  OP_THUMBNAIL,
  OP_LIST
} operation;

/* This struct is the "specification" for the flac-image APPLICATION data
   block.  The binary image data is prepended with this 72-byte header:
   
   vers - header structure version number.  The only defined value is
          0x0001.

   mimetype - 32 byte char buffer meant to describe the block content type
          (although this program could care less, and just treats the
	  mimetype field as a kind of label.)

   filename - 32 byte char buffer meant to record the name of the original
          file.  Programs are free to ignore this when extracting files.
	  This program stores the last component of the original filename
	  when importing, and uses the same name when exporting.

   datasize - number of bytes of binary data that follow the header.
*/

typedef struct {
  unsigned int vers;
  char mimetype[IMAGE_HEADER_MIMETYPE_MAXLEN];
  char filename[IMAGE_HEADER_FILENAME_MAXLEN];
  unsigned int datasize;
 } flac_image_header;



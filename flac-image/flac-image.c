/*
 * Cheesy hack to store and retrieve images (such as cover art) in APPLICATION
 * blocks in FLAC files.  Actually it turns out that you could store any
 * arbitrary files and differentiate them by mime-type if you wanted.  That's
 * because this program doesn't understand anything in particular about image
 * files; they are just treated as blobs of data.
 *
 * The application ID and data structure are defined in flac-image.h.
 *
 * Copyright (c) 2005 Michael A. Dickerson.  All rights reserved.  Copying, 
 * modification, redistribution, and use are permitted under the terms of a
 * BSD-style license described in the file "COPYING".
 *
 * Written 17 Jan 2005 MAD
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <FLAC/metadata.h>
#include "flac-image.h"

#define VERSION "1.00"

extern char *optarg;
extern int optind, opterr, optopt;

FLAC__Metadata_Chain *chain;
FLAC__Metadata_Iterator *iter;

void  search_images(char *mime_type, int extract);
void  delete_images(char *mime_type);
void  import_image(char *imgfile, char *mimetype);
void  export_thumbnail(void);
void  export_image_from_block(FLAC__StreamMetadata *block);
char *guess_mime_type(char *imgfile);
int   block_is_image(FLAC__StreamMetadata *block);
void  usage(void);

int main(int argc, char *argv[])
{
  int o, oper = OP_UNDEFINED, i;
  char *image_file = NULL, *mime_type = NULL;

  /* parse options */
  while ((o = getopt(argc, argv, "i:xt:dnl")) != -1) {
    switch (o) {
    case 'i':
      oper = OP_IMPORT;
      image_file = optarg;
      break;
    case 'x':
      oper = OP_EXPORT;
      break;
    case 'd':
      oper = OP_DELETE;
      break;
    case 'n':
      oper = OP_THUMBNAIL;
      break;
    case 'l':
      oper = OP_LIST;
      break; 
    case 't':
      mime_type = optarg;
      break;
    case '?':
      usage();
    }
  }
	 
  /* everything after optind should be a flac file name; if not, or if
     there is nothing left, that's an error. */
  if (optind >= argc) usage();

  for (i = optind; i < argc; ++i) {

    /* allocate a FLAC metadata chain pointer */
    chain = FLAC__metadata_chain_new();
    iter = FLAC__metadata_iterator_new();
    if (chain == NULL || iter == NULL) {
      fputs("ERROR: out of memory allocating chain.\n", stderr);
      return 1;
    }

    /* read blocks from flac file */
    if (FLAC__metadata_chain_read(chain, argv[i]) == false) {
      fprintf(stderr, "ERROR: can't read metadata from %s\n", argv[i]);
      return false;
    }

    FLAC__metadata_iterator_init(iter, chain);

    switch (oper) {
    case OP_IMPORT:
      import_image(image_file, mime_type);
      break;
    case OP_EXPORT:
      search_images(mime_type, true);
      break;
    case OP_DELETE:
      delete_images(mime_type);
      break;
    case OP_THUMBNAIL:
      export_thumbnail();
      break;
    case OP_LIST:
      search_images(mime_type, false);
      break;
    default:
      usage();
    }

    /* commit whatever operations were done */
    FLAC__metadata_iterator_delete(iter);
    /* fputs("Sorting padding...", stderr); */
    FLAC__metadata_chain_sort_padding(chain);
    /* fputs("done.\nWriting chain...", stderr); */
    if (FLAC__metadata_chain_write(chain, /*use_padding=*/true, 
				   /*preserve_stat=*/false) == false) {
      fputs("ERROR: can't write metadata chain\n", stderr);
      exit(3);
    }
    /* fputs("done.\n", stderr); */
    FLAC__metadata_chain_delete(chain);
  }
  
  return 0;
}

void delete_images(char *mime_type)
{
  FLAC__bool ok = true;
  FLAC__StreamMetadata *block;
  int count = 0;

  /* traverse the chain looking for only blocks of type APPLICATION with
     an application ID we recognize. */ 
  while (ok && FLAC__metadata_iterator_next(iter)) {
    block = FLAC__metadata_iterator_get_block(iter);
    if (!block_is_image(block)) continue;
    /* if a mime type was passed in, skip any blocks that don't match */
    if (mime_type) {
      flac_image_header *head = (flac_image_header *)block->data.application.data;
      if (strncmp(mime_type, head->mimetype, strlen(mime_type)) != 0) continue;
    }
    ok &= FLAC__metadata_iterator_delete_block(iter, /*replace_with_padding=*/true);
    ++count;
  }

 fprintf(stderr, "Deleted %d block(s).\n", count);
 return;
}

void import_image(char *imgfile, char *mimetype)
{
  struct stat img_stat;
  int blocklen, f;
  flac_image_header *img_header;
  FLAC__byte *img_data;
  FLAC__StreamMetadata *block;

  /* go to last block */
  while (FLAC__metadata_iterator_next(iter))
    ;

  if (stat(imgfile, &img_stat) != 0) {
    perror("ERROR: can't stat image file");
    return;
  }

  /* allocate enough bytes for a flac_image_header struct plus the file itself */
  blocklen = sizeof(flac_image_header) + img_stat.st_size;
  if ((img_data = malloc(blocklen)) == NULL) {
    fputs("ERROR: can't allocate memory for new image struct", stderr);
    return;
  }

  /* populate the header fields */
  img_header = (flac_image_header *)img_data;
  memset(img_header, 0, blocklen);
  img_header->vers = IMAGE_HEADER_VERSION;

  if (mimetype == NULL) mimetype = guess_mime_type(imgfile);
  strncpy(img_header->mimetype, mimetype, IMAGE_HEADER_MIMETYPE_MAXLEN);
  img_header->mimetype[IMAGE_HEADER_MIMETYPE_MAXLEN - 1] = 0;

  if (strrchr(imgfile, '/') != NULL) {
    /* store only the part of the filename after the final / */
    char *ptr = strrchr(imgfile, '/') + 1;
    strncpy(img_header->filename, ptr, IMAGE_HEADER_FILENAME_MAXLEN);
  } else {
    strncpy(img_header->filename, imgfile, IMAGE_HEADER_FILENAME_MAXLEN);
  }
  img_header->filename[IMAGE_HEADER_FILENAME_MAXLEN - 1] = 0;

  img_header->datasize = img_stat.st_size;

  /* read the image data into the buffer */
  if ((f = open(imgfile, O_RDONLY)) < 0) {
    perror("ERROR: can't open image file");
    return;
  }
  if (read(f, img_data + sizeof(flac_image_header), img_stat.st_size)
      < img_stat.st_size) {
    fputs("ERROR: short read trying to load image\n", stderr);
    close(f);
    return;
  }
  if (close(f)) {
    perror("WARNING: can't close file");
  }


  /* prepare a new block */
  if ((block = FLAC__metadata_object_new(FLAC__METADATA_TYPE_APPLICATION)) == NULL) {
    fputs("ERROR: can't allocate memory for new block", stderr);
    return;
  }
  memcpy(block->data.application.id, &APPLICATION_ID, ID_BYTES);
  FLAC__metadata_object_application_set_data(block, (FLAC__byte *)img_data,
					     blocklen, /*copy=*/ false);

  /* insert the new block to the stream */
  printf("Inserting block with mime-type %s: %d bytes\n", mimetype, blocklen);
  if (!FLAC__metadata_iterator_insert_block_after(iter, block))
    fputs("WARNING: block insert failed\n", stderr);

  return;
}

void search_images(char *mime_type, int extract)
{
  FLAC__bool ok = true;
  FLAC__StreamMetadata *block;
  int count = 0;

  while (ok && FLAC__metadata_iterator_next(iter)) {
    block = FLAC__metadata_iterator_get_block(iter);
    if (!block_is_image(block)) continue;

    flac_image_header *head = (flac_image_header *)block->data.application.data;

    /* if a mime type was passed in, skip any blocks that don't match */
    if (mime_type) {
      if (strncmp(mime_type, head->mimetype, strlen(mime_type)) != 0) continue;
    }

    fprintf(stdout, "Found image block: type %s, size %d\n",
	    head->mimetype, head->datasize);

    if (extract) {
      fprintf(stdout, "Extracting to file: %s\n", head->filename);
      export_image_from_block(block);
    } else {
      fprintf(stdout, "Name: %s\n", head->filename);
    }
    ++count;
  }

  fprintf(stderr, "Found %d recognized block(s).\n", count);
  return;
}

/*
 * export_thumbnail() walks the chain looking for the smallest block with
 * the right application ID and a mime-type that starts with image/, and
 * extracts only that image.
 */

void export_thumbnail(void)
{
  FLAC__StreamMetadata *block;
  FLAC__StreamMetadata *smallest_block = NULL;
  flac_image_header *head;
  int smallest_size = 10 * 1024 * 1024; /* start with a big value, 10 MB */

  /* traverse the chain and find the smallest block with our application ID
     and with a mime-type that matches 'image/' */
  while (FLAC__metadata_iterator_next(iter)) {
    block = FLAC__metadata_iterator_get_block(iter);
    /* skip blocks that don't match our application ID */
    if (!block_is_image(block)) continue;
    /* skip blocks that don't match mime-type image/ */
    head = (flac_image_header *)block->data.application.data;
    if (strncmp(head->mimetype, "image/", 6) != 0) continue;
    /* see whether this block is the smallest one so far */
    if (head->datasize < smallest_size) {
      smallest_block = block;
      smallest_size = head->datasize;
    }
  }

  if (smallest_block == NULL) {
    fputs("ERROR: No image blocks found.\n", stderr);
  } else {
    head = (flac_image_header *)smallest_block->data.application.data;
    fprintf(stdout, "Found image block: type %s, size %d\n",
	    head->mimetype, head->datasize);
    fprintf(stdout, "Extracting to file: %s\n", head->filename);
    export_image_from_block(smallest_block);
  }

}

/*
 * export_image_from_block() takes a pointer to a metadata block and
 * dumps the image to a file using the name stored in the block.  Does
 * nothing if block_is_image(block) returns false.
 */

void export_image_from_block(FLAC__StreamMetadata *block)
{
  flac_image_header *head;
  int datasize, fd;

  if (!block_is_image(block)) return;
  head = (flac_image_header *)block->data.application.data;
  datasize = head->datasize;

  /* sanity check: this program won't put / characters in stored filenames,
     but some joker could do it and trick you into overwriting e.g.
     ~/.ssh/authorized_keys */
  if (strchr(head->filename, '/') != NULL) {
    fputs("ERROR: won't extract to filename containing path characters!\n",
	  stderr);
    return;
  }

  if ((fd = open(head->filename, O_WRONLY | O_CREAT, 00644)) < 0) {
    perror("ERROR: can't open file");
    return;
  }
  head++; /* note that head advances by sizeof(flac_image_header), so it now
	     points to the binary data that comes after the header struct. */
  if (write(fd, head, datasize) < datasize) {
    fputs("WARNING: short write to file\n", stderr);
  }
  if (close(fd)) { perror("WARNING: can't close file"); }
}


/*
 * block_is_image() returns true iff the pointed-to block is an
 * APPLICATION block that matches our application ID.
 */

int block_is_image(FLAC__StreamMetadata *block)
{
  if (block == NULL) return false;
  if (block->type != FLAC__METADATA_TYPE_APPLICATION) return false;
  FLAC__byte *blockid = block->data.application.id;
  if (memcmp(blockid, APPLICATION_ID, ID_BYTES) != 0) return false;
  flac_image_header *head = (flac_image_header *)block->data.application.data;
  if (head->vers != IMAGE_HEADER_VERSION) {
    fputs("WARNING: Image block has mismatched version stamp.\n", stderr);
  }
  return true;
}

/*
 * guess_mime_type() supplies mime-type strings for filenames that
 * happen to end in .jpg, .png, or .gif.  For anything else it returns
 * the string "unknown".
 */

char *guess_mime_type(char *imgfilename)
{
  char *end;
  end = imgfilename;
  while (*end != 0) ++end;

  if (strcmp(end - 3, "jpg") == 0 || strcmp(end - 3, "JPG") == 0) {
    return "image/jpeg";
  } else if (strcmp(end - 4, "jpeg") == 0 || strcmp(end - 4, "JPEG") == 0) {
    return "image/jpeg";
  } else if (strcmp(end - 3, "png") == 0 || strcmp(end - 3, "PNG") == 0) {
    return "image/png";
  } else if (strcmp(end - 3, "gif") == 0 || strcmp(end - 3, "GIF") == 0) {
    return "image/gif";
  }
  
  return "unknown";
}

void usage(void)
{
  fprintf(stderr, "flac-image %s, Copyright (c) 2005 Michael A. Dickerson\n\n", VERSION);
  fputs("Usage:\n", stderr);
  fputs("flac-image (-x | -i <imagefile> | -d | -n | -l) [-t <mimetype>] flacfile ...\n", stderr);
  fputs("\n", stderr);
  fputs("   -x: eXtract images in flacfile to current directory\n", stderr);
  fputs("   -i: Insert image <imagefile> in flacfile\n", stderr);
  fputs("   -d: Delete image blocks in flacfile\n", stderr);
  fputs("   -n: extract only the smallest available image block (thumbNail)\n", stderr);
  fputs("   -l: List recognized image blocks\n\n", stderr);
  fputs("   -t: with -i, use <mimetype> instead of guessing based on filename\n", stderr);
  fputs("       with any other operation, process only the blocks that match <mimetype>\n\n", stderr);
  exit(1);
}

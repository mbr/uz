uz
==

Uz is a small tools to unpack files.

.. code-block:: sh

   $ uz -v sample.tar.xz
   sample_data/
   sample_data/bar


It does not infer file-types from file endings but analyzes headers instead:

.. code-block:: sh

   $ mv sample.tar.xz nothing-in-the-filename
   $ uz -l nothing-in-the-filename
   sample_data/
   sample_data/bar


It also does the right thing in weird cases:

.. code-block:: sh

   $ uz -A sample.tar.xz.bz2.gz.xz.gz.bz2
   sample.tar.xz.bz2.gz.xz.gz.bz2: BZip <- gzip <- xz <- gzip <- BZip <- xz <- tarfile
   cmd: bunzip2 --stdout | gunzip --to-stdout | xz --decompress --stdout | gunzip --to-stdout | bunzip2 --stdout | tar --extract --xz
   $ uz sample.tar.xz.bz2.gz.xz.gz.bz2
   $ ls
   sample_data  sample.tar.xz.bz2.gz.xz.gz.bz2


Supported fileformats
---------------------

It's fairly easy to add another archive or compression format to ``uz``; right
now it supports  ``.bz2``, ``.gz``, ``.xz`` and ``.7z``, ``.rar``, ``.tar``,
``.zip``, -- as well as all combinations of those.

More formats are added as soon as the author runs into a file he needs to
extract or via pull request.

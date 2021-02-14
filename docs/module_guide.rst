Using the ``yt_dlp`` module
===============================

When using the ``yt_dlp`` module, you start by creating an instance of :class:`YoutubeDL` and adding all the available extractors:

.. code-block:: python

    >>> from yt_dlp import YoutubeDL
    >>> ydl = YoutubeDL()
    >>> ydl.add_default_info_extractors()

Extracting video information
----------------------------

You use the :meth:`YoutubeDL.extract_info` method for getting the video information, which returns a dictionary:

.. code-block:: python

    >>> info = ydl.extract_info('http://www.youtube.com/watch?v=BaW_jenozKc', download=False)
    [youtube] Setting language
    [youtube] BaW_jenozKc: Downloading webpage
    [youtube] BaW_jenozKc: Downloading video info webpage
    [youtube] BaW_jenozKc: Extracting video information
    >>> info['title']
    'youtube-dlp test video "\'/\\ä↭𝕐'
    >>> info['height'], info['width']
    (720, 1280)

If you want to download or play the video you can get its url:

.. code-block:: python

    >>> info['url']
    'https://...'

Extracting playlist information
-------------------------------

The playlist information is extracted in a similar way, but the dictionary is a bit different:

.. code-block:: python

    >>> playlist = ydl.extract_info('http://www.ted.com/playlists/13/open_source_open_world', download=False)
    [TED] open_source_open_world: Downloading playlist webpage
    ...
    >>> playlist['title']
    'Open-source, open world'



You can access the videos in the playlist with the ``entries`` field:

.. code-block:: python

    >>> for video in playlist['entries']:
    ...     print('Video #%d: %s' % (video['playlist_index'], video['title']))

    Video #1: How Arduino is open-sourcing imagination
    Video #2: The year open data went worldwide
    Video #3: Massive-scale online collaboration
    Video #4: The art of asking
    Video #5: How cognitive surplus will change the world
    Video #6: The birth of Wikipedia
    Video #7: Coding a better government
    Video #8: The era of open innovation
    Video #9: The currency of the new economy is trust


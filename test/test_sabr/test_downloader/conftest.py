import tempfile
import uuid
from pathlib import Path
import pytest
from yt_dlp.downloader.sabr import SabrFD
from yt_dlp import YoutubeDL


@pytest.fixture
def fd(logger):
    with YoutubeDL({'logger': logger}) as ydl:
        yield SabrFD(ydl, {})


@pytest.fixture
def filename():
    # use tmp file module to generate a temporary filename
    with tempfile.TemporaryDirectory() as tmp:
        yield str(Path(tmp) / f'{uuid.uuid4()}.mp4')

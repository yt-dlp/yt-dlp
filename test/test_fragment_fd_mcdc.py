import pytest
import time
from yt_dlp.downloader.fragment import FragmentFD
from yt_dlp.utils import DownloadError
from unittest.mock import Mock


class DummyDestStream:
    def __init__(self):
        self.contents = []

    def write(self, data):
        self.contents.append(data)

    def flush(self):
        pass

    def close(self):
        pass


@pytest.fixture
def dummy_ctx():
    return {
        'filename': 'testfile',
        'fragment_index': 0,
        'dest_stream': DummyDestStream(),
        'live': False,
        'tmpfilename': 'testfile.part',
        'started': time.time(),
        'total_bytes': 0,
    }


@pytest.fixture
def dummy_info_dict():
    return {
        'http_headers': {},
    }


@pytest.fixture
def dummy_fragment():
    return {
        'frag_index': 0,
        'url': 'http://dummy.url/frag0.ts',
        'fragment_count': 1,
    }


@pytest.fixture
def fd():
    fake_ydl = Mock()
    fake_ydl._progress_hooks = []
    fake_ydl._postprocessors = []
    for name in [
        'deprecation_warning', 'report_error', 'report_warning',
        'to_screen', 'to_console_title',
    ]:
        setattr(fake_ydl, name, Mock())

    return FragmentFD(fake_ydl, {
        'fragment_retries': 0,
        'skip_unavailable_fragments': True,
        'noprogress': True,
    })


def test_ct1_fragment_ok(fd, dummy_ctx, dummy_info_dict, dummy_fragment, monkeypatch):
    """CT1 - Fragmento comum, leitura e escrita sem falhas"""

    dummy_fragment['url'] = 'http://example.com/video-frag.ts'

    monkeypatch.setattr(fd, '_download_fragment', lambda *a, **k: True)
    monkeypatch.setattr(fd, '_read_fragment', lambda ctx: b'data')
    monkeypatch.setattr(fd, '_append_fragment', lambda ctx, content: ctx['dest_stream'].write(content))
    monkeypatch.setattr(fd, 'try_rename', lambda *a, **k: None)
    monkeypatch.setattr(fd.ydl, 'run_all_postprocessors', lambda *a, **k: ([], True))

    fd.decrypter = lambda info: lambda fragment, content: content

    result = fd.download_and_append_fragments(dummy_ctx, [dummy_fragment], dummy_info_dict)

    assert dummy_ctx['dest_stream'].contents == [b'data']
    assert result is False


def test_ct2_fragment_skip(fd, dummy_ctx, dummy_info_dict, dummy_fragment, monkeypatch):
    """CT2 - Fragmento falha na leitura, mas não é fatal: deve ser ignorado"""

    dummy_fragment['frag_index'] = 1
    dummy_fragment['byte_range'] = {'start': 0, 'end': 999}

    monkeypatch.setattr(fd, '_download_fragment', lambda *a, **k: True)
    monkeypatch.setattr(fd, '_read_fragment', lambda ctx: None)
    monkeypatch.setattr(fd, 'try_rename', lambda *a, **k: None)
    monkeypatch.setattr(fd.ydl, 'run_all_postprocessors', lambda *a, **k: ([], True))

    skipped = []
    monkeypatch.setattr(fd, 'report_skip_fragment', lambda idx, reason=None: skipped.append(idx))

    fd.decrypter = lambda info: lambda fragment, content: content

    result = fd.download_and_append_fragments(dummy_ctx, [dummy_fragment], dummy_info_dict)

    assert skipped == [1]
    assert result is False


def test_ct3_fragment_fatal_error(fd, dummy_ctx, dummy_info_dict, dummy_fragment, monkeypatch):
    """CT3 - Falha de leitura fatal: deve interromper o processo"""

    monkeypatch.setattr(fd, '_download_fragment', lambda *a, **k: True)
    monkeypatch.setattr(fd, '_read_fragment', lambda ctx: None)
    monkeypatch.setattr(fd, '_append_fragment', lambda ctx, c: (_ for _ in ()).throw(Exception("Shouldn't append")))

    fd.decrypter = lambda info: lambda fragment, content: content

    errors = []
    monkeypatch.setattr(fd, 'report_error', lambda msg, **kwargs: errors.append(msg))

    def is_fatal(index):
        return True

    result = fd.download_and_append_fragments(dummy_ctx, [dummy_fragment], dummy_info_dict, is_fatal=is_fatal)

    assert result is False
    assert any('fragment' in e.lower() and 'unable to continue' in e.lower() for e in errors)


def test_ct4_downloaderror_fatal(fd, dummy_ctx, dummy_info_dict, dummy_fragment, monkeypatch):
    """CT4 - Erro de download fatal: exceção deve ser lançada"""

    def raise_download_error(*a, **k):
        raise DownloadError('Erro no download do fragmento')

    monkeypatch.setattr(fd, '_download_fragment', raise_download_error)
    monkeypatch.setattr(fd, '_read_fragment', lambda ctx: b'data')  # Nunca será chamado

    fd.decrypter = lambda info: lambda fragment, content: content

    def is_fatal(index):
        return True

    with pytest.raises(DownloadError, match='Erro no download'):
        fd.download_and_append_fragments(dummy_ctx, [dummy_fragment], dummy_info_dict, is_fatal=is_fatal)

tests = {
    'webp': lambda h: h[0:4] == b'RIFF' and h[8:] == b'WEBP',
    'png': lambda h: h[:8] == b'\211PNG\r\n\032\n',
    'jpeg': lambda h: h[6:10] in (b'JFIF', b'Exif'),
}


def what(path):
    """Detect format of image (Currently supports jpeg, png, webp only)
    Ref: https://github.com/python/cpython/blob/3.10/Lib/imghdr.py
    """
    with open(path, 'rb') as f:
        head = f.read(12)
    return next((type_ for type_, test in tests.items() if test(head)), None)

def what(file=None, h=None):
    """ Detect format of image (Currently supports jpeg, png, webp, gif only) """
    if h is None:
        with open(file, 'rb') as f:
            h = f.read(12)

    if h.startswith(b'RIFF') and h.startswith(b'WEBP', 8):
        return 'webp'

    if h.startswith(b'\x89PNG'):
        return 'png'

    if h.startswith(b'\xFF\xD8\xFF'):
        return 'jpeg'

    if h.startswith(b'GIF'):
        return 'gif'

    return None

from . import HlsFD

from ..aes import aes_cbc_decrypt_bytes, unpad_pkcs7


class ShortMaxFD(HlsFD):
    """
    Special downloader for ShortMax videos.
    Overriding decrypter is needed because ShortMax .ts fragments hardcode iv and key at its header along with encrypted data.

    Note, this is not a part of public API, and will be removed without notice.
    DO NOT USE
    """

    def decrypter(self, info_dict):
        def decrypt_fragment(fragment, frag_content):
            if frag_content is None:
                return
            header_size = 0x400
            header = frag_content[:header_size]
            iv = b'shortmax00000000'
            key_offset = int(header[0x10:0x14].decode('ascii'))
            encrypted_length = int(header[0x14:0x18].decode('ascii'))
            key = header[key_offset:key_offset + 16]
            encrypted = frag_content[header_size:header_size + encrypted_length]
            tail = frag_content[header_size + encrypted_length:]
            decrypted = unpad_pkcs7(aes_cbc_decrypt_bytes(encrypted, key, iv))
            return decrypted + tail
        return decrypt_fragment

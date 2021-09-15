#!/usr/bin/env python3
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.aes import (
    fb_aes_decrypt,
    fb_aes_encrypt,
    fb_aes_cbc_decrypt,
    fb_aes_cbc_encrypt,
    fb_aes_ctr_decrypt,
    fb_aes_ctr_encrypt,
    fb_aes_gcm_decrypt_and_verify,
    aes_decrypt,
    aes_encrypt,
    aes_cbc_decrypt,
    aes_cbc_encrypt,
    aes_ctr_decrypt,
    aes_ctr_encrypt,
    aes_gcm_decrypt_and_verify,
    aes_decrypt_text,
    key_expansion,
    BLOCK_SIZE_BYTES
)
from yt_dlp.compat import compat_crypto_AES
from yt_dlp.utils import bytes_to_intlist, intlist_to_bytes
import base64

# the encrypted data can be generate with 'devscripts/generate_aes_testdata.py'


class TestAES(unittest.TestCase):
    def setUp(self):
        self.key = self.iv = [0x20, 0x15] + 14 * [0]
        self.secret_msg = b'Secret message goes here'

    def test_encrypt(self):
        key = list(range(16))
        fb_encrypted = fb_aes_encrypt(bytes_to_intlist(self.secret_msg), key_expansion(key))
        fb_decrypted = intlist_to_bytes(fb_aes_decrypt(fb_encrypted, key_expansion(key)))
        self.assertEqual(fb_decrypted, self.secret_msg[:BLOCK_SIZE_BYTES])
        if compat_crypto_AES:
            encrypted = aes_encrypt(self.secret_msg, intlist_to_bytes(key))
            decrypted = aes_decrypt(encrypted, intlist_to_bytes(key))
            self.assertEqual(encrypted, intlist_to_bytes(fb_encrypted))
            self.assertEqual(decrypted, self.secret_msg[:BLOCK_SIZE_BYTES])

    def test_cbc_decrypt(self):
        data = bytes_to_intlist(
            b"\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6'\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd"
        )
        fb_decrypted = intlist_to_bytes(fb_aes_cbc_decrypt(data, self.key, self.iv))
        self.assertEqual(fb_decrypted.rstrip(b'\x08'), self.secret_msg)
        if compat_crypto_AES:
            decrypted = aes_cbc_decrypt(*map(intlist_to_bytes, (data, self.key, self.iv)))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_cbc_encrypt(self):
        data = bytes_to_intlist(self.secret_msg)
        fb_encrypted = intlist_to_bytes(fb_aes_cbc_encrypt(data, self.key, self.iv))
        self.assertEqual(
            fb_encrypted,
            b"\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6'\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd"
        )
        if compat_crypto_AES:
            encrypted = aes_cbc_encrypt(*map(intlist_to_bytes, (data, self.key, self.iv)))
            self.assertEqual(
                encrypted,
                b"\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6'\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd")

    def test_ctr_decrypt(self):
        data = bytes_to_intlist(
            b"\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08"
        )
        fb_decrypted = intlist_to_bytes(fb_aes_ctr_decrypt(data, self.key, self.iv))
        self.assertEqual(fb_decrypted.rstrip(b'\x08'), self.secret_msg)
        if compat_crypto_AES:
            decrypted = aes_ctr_decrypt(*map(intlist_to_bytes, (data, self.key, self.iv)))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_ctr_encrypt(self):
        data = bytes_to_intlist(self.secret_msg)
        fb_encrypted = intlist_to_bytes(fb_aes_ctr_encrypt(data, self.key, self.iv))
        self.assertEqual(
            fb_encrypted,
            b"\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08"
        )
        if compat_crypto_AES:
            encrypted = aes_ctr_encrypt(*map(intlist_to_bytes, (data, self.key, self.iv)))
            self.assertEqual(
                encrypted,
                b"\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08"
            )

    def test_gcm_decrypt(self):
        data = bytes_to_intlist(b"\x159Y\xcf5eud\x90\x9c\x85&]\x14\x1d\x0f.\x08\xb4T\xe4/\x17\xbd")
        authentication_tag = bytes_to_intlist(b"\xe8&I\x80rI\x07\x9d}YWuU@:e")

        fb_decrypted = intlist_to_bytes(fb_aes_gcm_decrypt_and_verify(data, self.key, authentication_tag, self.iv[:12]))
        self.assertEqual(fb_decrypted.rstrip(b'\x08'), self.secret_msg)
        if compat_crypto_AES:
            decrypted = aes_gcm_decrypt_and_verify(*map(intlist_to_bytes, (data,
                                                                           self.key,
                                                                           authentication_tag,
                                                                           self.iv[:12]))
                                                   )
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_decrypt_text(self):
        password = intlist_to_bytes(self.key).decode('utf-8')
        encrypted = base64.b64encode(
            intlist_to_bytes(self.iv[:8])
            + b'\x17\x15\x93\xab\x8d\x80V\xcdV\xe0\t\xcdo\xc2\xa5\xd8ksM\r\xe27N\xae'
        ).decode('utf-8')
        decrypted = aes_decrypt_text(encrypted, password, 16)
        self.assertEqual(decrypted, self.secret_msg)
        if compat_crypto_AES:
            decrypted = aes_decrypt_text(encrypted, password, 16)
            self.assertEqual(decrypted, self.secret_msg)

        password = intlist_to_bytes(self.key).decode('utf-8')
        encrypted = base64.b64encode(
            intlist_to_bytes(self.iv[:8])
            + b'\x0b\xe6\xa4\xd9z\x0e\xb8\xb9\xd0\xd4i_\x85\x1d\x99\x98_\xe5\x80\xe7.\xbf\xa5\x83'
        ).decode('utf-8')
        decrypted = aes_decrypt_text(encrypted, password, 32)
        self.assertEqual(decrypted, self.secret_msg)


if __name__ == '__main__':
    unittest.main()

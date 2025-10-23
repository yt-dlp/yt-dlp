#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import base64

from yt_dlp.aes import (
    aes_cbc_decrypt,
    aes_cbc_decrypt_bytes,
    aes_cbc_encrypt,
    aes_ctr_decrypt,
    aes_ctr_encrypt,
    aes_decrypt,
    aes_decrypt_text,
    aes_ecb_decrypt,
    aes_ecb_encrypt,
    aes_encrypt,
    aes_gcm_decrypt_and_verify,
    aes_gcm_decrypt_and_verify_bytes,
    key_expansion,
    pad_block,
)
from yt_dlp.dependencies import Cryptodome

# the encrypted data can be generate with 'devscripts/generate_aes_testdata.py'


class TestAES(unittest.TestCase):
    def setUp(self):
        self.key = self.iv = [0x20, 0x15] + 14 * [0]
        self.secret_msg = b'Secret message goes here'

    def test_encrypt(self):
        msg = b'message'
        key = list(range(16))
        encrypted = aes_encrypt(list(msg), key)
        decrypted = bytes(aes_decrypt(encrypted, key))
        self.assertEqual(decrypted, msg)

    def test_cbc_decrypt(self):
        data = b'\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6\x27\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd'
        decrypted = bytes(aes_cbc_decrypt(list(data), self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)
        if Cryptodome.AES:
            decrypted = aes_cbc_decrypt_bytes(data, bytes(self.key), bytes(self.iv))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_cbc_encrypt(self):
        data = list(self.secret_msg)
        encrypted = bytes(aes_cbc_encrypt(data, self.key, self.iv))
        self.assertEqual(
            encrypted,
            b'\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6\'\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd')

    def test_ctr_decrypt(self):
        data = list(b'\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08')
        decrypted = bytes(aes_ctr_decrypt(data, self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_ctr_encrypt(self):
        data = list(self.secret_msg)
        encrypted = bytes(aes_ctr_encrypt(data, self.key, self.iv))
        self.assertEqual(
            encrypted,
            b'\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08')

    def test_gcm_decrypt(self):
        data = b'\x159Y\xcf5eud\x90\x9c\x85&]\x14\x1d\x0f.\x08\xb4T\xe4/\x17\xbd'
        authentication_tag = b'\xe8&I\x80rI\x07\x9d}YWuU@:e'

        decrypted = bytes(aes_gcm_decrypt_and_verify(
            list(data), self.key, list(authentication_tag), self.iv[:12]))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)
        if Cryptodome.AES:
            decrypted = aes_gcm_decrypt_and_verify_bytes(
                data, bytes(self.key), authentication_tag, bytes(self.iv[:12]))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_gcm_aligned_decrypt(self):
        data = b'\x159Y\xcf5eud\x90\x9c\x85&]\x14\x1d\x0f'
        authentication_tag = b'\x08\xb1\x9d!&\x98\xd0\xeaRq\x90\xe6;\xb5]\xd8'

        decrypted = bytes(aes_gcm_decrypt_and_verify(
            list(data), self.key, list(authentication_tag), self.iv[:12]))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg[:16])
        if Cryptodome.AES:
            decrypted = aes_gcm_decrypt_and_verify_bytes(
                data, bytes(self.key), authentication_tag, bytes(self.iv[:12]))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg[:16])

    def test_decrypt_text(self):
        password = bytes(self.key).decode()
        encrypted = base64.b64encode(
            bytes(self.iv[:8])
            + b'\x17\x15\x93\xab\x8d\x80V\xcdV\xe0\t\xcdo\xc2\xa5\xd8ksM\r\xe27N\xae',
        ).decode()
        decrypted = (aes_decrypt_text(encrypted, password, 16))
        self.assertEqual(decrypted, self.secret_msg)

        password = bytes(self.key).decode()
        encrypted = base64.b64encode(
            bytes(self.iv[:8])
            + b'\x0b\xe6\xa4\xd9z\x0e\xb8\xb9\xd0\xd4i_\x85\x1d\x99\x98_\xe5\x80\xe7.\xbf\xa5\x83',
        ).decode()
        decrypted = (aes_decrypt_text(encrypted, password, 32))
        self.assertEqual(decrypted, self.secret_msg)

    def test_ecb_encrypt(self):
        data = list(self.secret_msg)
        encrypted = bytes(aes_ecb_encrypt(data, self.key))
        self.assertEqual(
            encrypted,
            b'\xaa\x86]\x81\x97>\x02\x92\x9d\x1bR[[L/u\xd3&\xd1(h\xde{\x81\x94\xba\x02\xae\xbd\xa6\xd0:')

    def test_ecb_decrypt(self):
        data = list(b'\xaa\x86]\x81\x97>\x02\x92\x9d\x1bR[[L/u\xd3&\xd1(h\xde{\x81\x94\xba\x02\xae\xbd\xa6\xd0:')
        decrypted = bytes(aes_ecb_decrypt(data, self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_key_expansion(self):
        key = '4f6bdaa39e2f8cb07f5e722d9edef314'

        self.assertEqual(key_expansion(list(bytearray.fromhex(key))), [
            0x4F, 0x6B, 0xDA, 0xA3, 0x9E, 0x2F, 0x8C, 0xB0, 0x7F, 0x5E, 0x72, 0x2D, 0x9E, 0xDE, 0xF3, 0x14,
            0x53, 0x66, 0x20, 0xA8, 0xCD, 0x49, 0xAC, 0x18, 0xB2, 0x17, 0xDE, 0x35, 0x2C, 0xC9, 0x2D, 0x21,
            0x8C, 0xBE, 0xDD, 0xD9, 0x41, 0xF7, 0x71, 0xC1, 0xF3, 0xE0, 0xAF, 0xF4, 0xDF, 0x29, 0x82, 0xD5,
            0x2D, 0xAD, 0xDE, 0x47, 0x6C, 0x5A, 0xAF, 0x86, 0x9F, 0xBA, 0x00, 0x72, 0x40, 0x93, 0x82, 0xA7,
            0xF9, 0xBE, 0x82, 0x4E, 0x95, 0xE4, 0x2D, 0xC8, 0x0A, 0x5E, 0x2D, 0xBA, 0x4A, 0xCD, 0xAF, 0x1D,
            0x54, 0xC7, 0x26, 0x98, 0xC1, 0x23, 0x0B, 0x50, 0xCB, 0x7D, 0x26, 0xEA, 0x81, 0xB0, 0x89, 0xF7,
            0x93, 0x60, 0x4E, 0x94, 0x52, 0x43, 0x45, 0xC4, 0x99, 0x3E, 0x63, 0x2E, 0x18, 0x8E, 0xEA, 0xD9,
            0xCA, 0xE7, 0x7B, 0x39, 0x98, 0xA4, 0x3E, 0xFD, 0x01, 0x9A, 0x5D, 0xD3, 0x19, 0x14, 0xB7, 0x0A,
            0xB0, 0x4E, 0x1C, 0xED, 0x28, 0xEA, 0x22, 0x10, 0x29, 0x70, 0x7F, 0xC3, 0x30, 0x64, 0xC8, 0xC9,
            0xE8, 0xA6, 0xC1, 0xE9, 0xC0, 0x4C, 0xE3, 0xF9, 0xE9, 0x3C, 0x9C, 0x3A, 0xD9, 0x58, 0x54, 0xF3,
            0xB4, 0x86, 0xCC, 0xDC, 0x74, 0xCA, 0x2F, 0x25, 0x9D, 0xF6, 0xB3, 0x1F, 0x44, 0xAE, 0xE7, 0xEC])

    def test_pad_block(self):
        block = [0x21, 0xA0, 0x43, 0xFF]

        self.assertEqual(pad_block(block, 'pkcs7'),
                         [*block, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C, 0x0C])

        self.assertEqual(pad_block(block, 'iso7816'),
                         [*block, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        self.assertEqual(pad_block(block, 'whitespace'),
                         [*block, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20])

        self.assertEqual(pad_block(block, 'zero'),
                         [*block, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        block = list(range(16))
        for mode in ('pkcs7', 'iso7816', 'whitespace', 'zero'):
            self.assertEqual(pad_block(block, mode), block, mode)


if __name__ == '__main__':
    unittest.main()

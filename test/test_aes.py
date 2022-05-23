#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64

from yt_dlp.aes import (
    BLOCK_SIZE_BYTES,
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
)
from yt_dlp.dependencies import Cryptodome_AES
from yt_dlp.utils import bytes_to_intlist, intlist_to_bytes

# the encrypted data can be generate with 'devscripts/generate_aes_testdata.py'


class TestAES(unittest.TestCase):
    def setUp(self):
        self.key = self.iv = [0x20, 0x15] + 14 * [0]
        self.secret_msg = b'Secret message goes here'

    def test_encrypt(self):
        msg = b'message'
        key = list(range(16))
        encrypted = aes_encrypt(bytes_to_intlist(msg), key)
        decrypted = intlist_to_bytes(aes_decrypt(encrypted, key))
        self.assertEqual(decrypted, msg)

    def test_cbc_decrypt(self):
        data = b'\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6\x27\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd'
        decrypted = intlist_to_bytes(aes_cbc_decrypt(bytes_to_intlist(data), self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)
        if Cryptodome_AES:
            decrypted = aes_cbc_decrypt_bytes(data, intlist_to_bytes(self.key), intlist_to_bytes(self.iv))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_cbc_encrypt(self):
        data = bytes_to_intlist(self.secret_msg)
        encrypted = intlist_to_bytes(aes_cbc_encrypt(data, self.key, self.iv))
        self.assertEqual(
            encrypted,
            b'\x97\x92+\xe5\x0b\xc3\x18\x91ky9m&\xb3\xb5@\xe6\'\xc2\x96.\xc8u\x88\xab9-[\x9e|\xf1\xcd')

    def test_ctr_decrypt(self):
        data = bytes_to_intlist(b'\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08')
        decrypted = intlist_to_bytes(aes_ctr_decrypt(data, self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_ctr_encrypt(self):
        data = bytes_to_intlist(self.secret_msg)
        encrypted = intlist_to_bytes(aes_ctr_encrypt(data, self.key, self.iv))
        self.assertEqual(
            encrypted,
            b'\x03\xc7\xdd\xd4\x8e\xb3\xbc\x1a*O\xdc1\x12+8Aio\xd1z\xb5#\xaf\x08')

    def test_gcm_decrypt(self):
        data = b'\x159Y\xcf5eud\x90\x9c\x85&]\x14\x1d\x0f.\x08\xb4T\xe4/\x17\xbd'
        authentication_tag = b'\xe8&I\x80rI\x07\x9d}YWuU@:e'

        decrypted = intlist_to_bytes(aes_gcm_decrypt_and_verify(
            bytes_to_intlist(data), self.key, bytes_to_intlist(authentication_tag), self.iv[:12]))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)
        if Cryptodome_AES:
            decrypted = aes_gcm_decrypt_and_verify_bytes(
                data, intlist_to_bytes(self.key), authentication_tag, intlist_to_bytes(self.iv[:12]))
            self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)

    def test_decrypt_text(self):
        password = intlist_to_bytes(self.key).decode()
        encrypted = base64.b64encode(
            intlist_to_bytes(self.iv[:8])
            + b'\x17\x15\x93\xab\x8d\x80V\xcdV\xe0\t\xcdo\xc2\xa5\xd8ksM\r\xe27N\xae'
        ).decode()
        decrypted = (aes_decrypt_text(encrypted, password, 16))
        self.assertEqual(decrypted, self.secret_msg)

        password = intlist_to_bytes(self.key).decode()
        encrypted = base64.b64encode(
            intlist_to_bytes(self.iv[:8])
            + b'\x0b\xe6\xa4\xd9z\x0e\xb8\xb9\xd0\xd4i_\x85\x1d\x99\x98_\xe5\x80\xe7.\xbf\xa5\x83'
        ).decode()
        decrypted = (aes_decrypt_text(encrypted, password, 32))
        self.assertEqual(decrypted, self.secret_msg)

    def test_ecb_encrypt(self):
        data = bytes_to_intlist(self.secret_msg)
        data += [0x08] * (BLOCK_SIZE_BYTES - len(data) % BLOCK_SIZE_BYTES)
        encrypted = intlist_to_bytes(aes_ecb_encrypt(data, self.key, self.iv))
        self.assertEqual(
            encrypted,
            b'\xaa\x86]\x81\x97>\x02\x92\x9d\x1bR[[L/u\xd3&\xd1(h\xde{\x81\x94\xba\x02\xae\xbd\xa6\xd0:')

    def test_ecb_decrypt(self):
        data = bytes_to_intlist(b'\xaa\x86]\x81\x97>\x02\x92\x9d\x1bR[[L/u\xd3&\xd1(h\xde{\x81\x94\xba\x02\xae\xbd\xa6\xd0:')
        decrypted = intlist_to_bytes(aes_ecb_decrypt(data, self.key, self.iv))
        self.assertEqual(decrypted.rstrip(b'\x08'), self.secret_msg)


if __name__ == '__main__':
    unittest.main()

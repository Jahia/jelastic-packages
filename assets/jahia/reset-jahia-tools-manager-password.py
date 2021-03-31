#!/usr/bin/env python3

import fileinput
import sys
from os import urandom
from hashlib import pbkdf2_hmac
from binascii import b2a_base64, a2b_base64

new_password = a2b_base64(str.encode(sys.argv[1]))
file_path = sys.argv[2]

salt = urandom(64)
new_password_hash_bytes = pbkdf2_hmac('sha1', new_password, salt, 8192, 32)

# bytes to string
new_password_hash = b2a_base64(new_password_hash_bytes, newline=False).decode("utf-8")
new_salt = b2a_base64(salt, newline=False).decode("utf-8")

with fileinput.FileInput(file_path, inplace=True, backup='.bak') as file:
    for line in file:
        if line.startswith('jahiaToolManagerPassword'):
            line = "jahiaToolManagerPassword = p:" + new_salt + "$" + new_password_hash + "\n"
        print(line, end='')

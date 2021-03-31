#!/usr/bin/env python3

import fileinput
import sys
from binascii import a2b_base64
import re
import crypt

file_path = sys.argv[1]
enable = sys.argv[2] == "true"

if enable:
    new_login = sys.argv[3]
    new_password = a2b_base64(str.encode(sys.argv[4])).decode("utf-8")
    new_password_hash = crypt.crypt(new_password, crypt.mksalt(crypt.METHOD_SHA512))


with fileinput.FileInput(file_path, inplace=True) as file:
    for line in file:
        if enable:
            # Uncomment line ending by #HTTP_AUTH_BASIC
            line = re.sub(r'^(\s*)#(.*#HTTP_AUTH_BASIC.*)$',
                          r'\1\2',
                          line)
            # update login/password
            line = re.sub(r'^(\s*user).*( password).*$',
                          r'\1 ' + new_login + r' \2 ' + new_password_hash,
                          line)
        else:
            line = re.sub(r'^(\s*)(#?)(.*)(#HTTP_AUTH_BASIC.*)$',
                          r'\1#\3\4',
                          line)

        print(line, end='')

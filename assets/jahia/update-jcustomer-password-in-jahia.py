#!/usr/bin/env python3

import fileinput
import sys
from binascii import a2b_base64

file_path = sys.argv[1]
new_password = a2b_base64(str.encode(sys.argv[2])).decode("utf-8")

with fileinput.FileInput(file_path, inplace=True, backup='.bak') as file:
    for line in file:
        if 'jexperience.jCustomerPassword' in line:
            line = "jexperience.jCustomerPassword=" + new_password + "\n"

        print(line, end='')

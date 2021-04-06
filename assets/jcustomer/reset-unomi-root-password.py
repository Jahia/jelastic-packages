#!/usr/bin/env python3

import fileinput
import sys
from binascii import a2b_base64
import re
import os.path

new_password = a2b_base64(str.encode(sys.argv[1])).decode("utf-8")
unomi_env_file = sys.argv[2]
datadog_conf_file = sys.argv[3]

pwd_set = False
password_line = "export UNOMI_ROOT_PASSWORD=" + new_password
with fileinput.FileInput(unomi_env_file, inplace=True) as file:
    for line in file:
        if "UNOMI_ROOT_PASSWORD" in line:
            line = password_line
            pwd_set = True
        print(line, end='')
if not pwd_set:
    with open(unomi_env_file, "a") as file:
        file.write(password_line)

if not os.path.exists(datadog_conf_file):
    exit(0)

with fileinput.FileInput(datadog_conf_file, inplace=True) as file:
    for line in file:
        line = re.sub(r'^(\s*password:).*$', r'\1 ' + new_password, line)
        print(line, end='')

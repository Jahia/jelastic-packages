#!/usr/bin/env python3
import argparse

def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number",
                        help="decimal number to set in file",
                        type=int)
    parser.add_argument("-f", "--file",
                        help="target file",
                        default="/data/digital-factory-data/repository/revisionNode")
    parser.add_argument("-r", "--read",
                        action="store_true",
                        help="if you want to read the file instead of write it")
    return parser.parse_args()


def write(n, f):
    with open(f, 'wb') as file:
        file.write((n).to_bytes(8, byteorder='big', signed=False))

def read(f):
    with open(f, 'rb') as file:
        print(int.from_bytes(file.read(), byteorder='big'))


if __name__ == '__main__':
    args = argparser()

    if args.read:
        read(args.file)
    elif args.number >= 0 and args.file:
        write(args.number, args.file)
    else:
        quit()

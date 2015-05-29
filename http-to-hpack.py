#!/usr/bin/env python3
import argparse
from hpack import hpack
import os
import random
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


def shuffle_string(string):
    l = list(string)
    random.shuffle(l)
    return "".join(l)


def read_headers(filename):
    size = 0
    headers = []
    with open(filename) as f:
        for line in f:
            size += len(line) + 1
            if not line:
                break
            if not headers:
                method, path, _ = line.split(" ")
                headers.append((":method", method))
                headers.append((":path", path))
            else:
                headers.append([v.strip() for v in line.split(":", maxsplit=1)])
    return size, headers


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("http_header_files", nargs="+")
    args = parser.parse_args()

    encoder = hpack.Encoder()

    for i, filename in enumerate(args.http_header_files, start=1):
        http1_size, headers = read_headers(filename)

        print("Header size for header %s in HTTP/1.1: %s bytes" % (i, http1_size))

        encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        print("Header size for header %s in HTTP/2: %s bytes" % (i, sum(map(len, encoded_headers))))
        print()

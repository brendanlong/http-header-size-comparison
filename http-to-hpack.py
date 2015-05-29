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
    sorted_encoder = hpack.Encoder()

    for i, filename in enumerate(args.http_header_files, start=1):
        print(filename)
        http1_size, headers = read_headers(filename)

        print("Header size for headers %s in HTTP/1.1: %s bytes" % (i, http1_size))

        encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        print("Header size for headers %s in HTTP/2: %s bytes" % (i, sum(map(len, encoded_headers))))

        # Sort query string to make it easier to compress repeatedly
        path = headers[1][1]
        parts = urlparse(path)
        query = parse_qs(parts.query)
        sorted_query = [(key, value[0]) for key, value in sorted(query.items())]
        sorted_query.sort(key=lambda x: x[0] == "id")
        headers[1] = ":path", urlunparse(("", "", parts.path, "", urlencode(sorted_query), ""))

        encoded_headers = [sorted_encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        print("Header size for headers (using sorted query string) %s in HTTP/2: %s bytes" % (i, sum(map(len, encoded_headers))))
        print()
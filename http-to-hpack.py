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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("http_header_files", nargs="+")
    args = parser.parse_args()

    size = 0
    headers = []

    with open(args.http_header_file) as f:
        for line in f:
            size += len(line) + 1
            if not line:
                break
            if not headers:
                method, path, _ = line.split(" ")
                headers.append((":method", method))
                headers.append((":path", path))
                first = False
            else:
                headers.append([v.strip() for v in line.split(":", maxsplit=1)])

    print("Header size for HTTP/1.1: %s bytes" % size)

    encoder = hpack.Encoder()
    encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                       for key, value in headers]
    print("Header size for HTTP/2 on first request: %s bytes" % sum(map(len, encoded_headers)))

    encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                       for key, value in headers]
    print("Header size for HTTP/2 on subsequent requests with same path: %s bytes" % sum(map(len, encoded_headers)))

    # change id in query string
    o = urlparse(path)
    query = parse_qs(o.query)
    if "id" in query:
        query["id"] = shuffle_string(query["id"])
        query = {key: value[0] for key, value in query.items()}
        headers[1] = ":path", urlunparse((o.scheme, o.netloc, o.path, o.params, urlencode(query), o.fragment))
        encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        print("Header size for HTTP/2 on subsequent requests with similar path: %s bytes" % sum(map(len, encoded_headers)))

    # completely change path
    headers[1] = ":path", shuffle_string(path)
    encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                       for key, value in headers]
    print("Header size for HTTP/2 on subsequent requests with completely different path: %s bytes" % \
        sum(map(len, encoded_headers)))

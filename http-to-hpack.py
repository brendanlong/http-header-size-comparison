#!/usr/bin/env python3
import argparse
from hpack import hpack
import logging
import os
import random
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


HTTP2_FRAME_OVERHEAD = 9 # See section 4.1: Frame Format



def shuffle_string(string):
    l = list(string)
    random.shuffle(l)
    return "".join(l)


def read_headers(filename):
    size = 2
    headers = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if not line:
                break
            size += len(line) + 2
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
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO if args.verbose else logging.WARNING)

    encoder = hpack.Encoder()
    encoder_no_path = hpack.Encoder()

    total_http1 = 0
    total_http2 = 0
    total_http2_no_path = 0

    for i, filename in enumerate(args.http_header_files, start=1):
        logging.info(filename)
        http1_size, headers = read_headers(filename)

        logging.info("Header size for headers %s in HTTP/1.1: %s bytes" % (i, http1_size))

        encoded_headers = [encoder.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        http2_size = sum(map(len, encoded_headers)) + HTTP2_FRAME_OVERHEAD
        logging.info("Header size for headers %s in HTTP/2: %s bytes" % (i, http2_size))

        encoded_headers = [encoder_no_path.add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers
                           if key != ":path"]
        http2_no_path_size = sum(map(len, encoded_headers)) + HTTP2_FRAME_OVERHEAD
        logging.info("Header size for headers %s excluding :path in HTTP/2: %s bytes" % (i, http2_no_path_size))


        logging.info("")
        total_http1 += http1_size
        total_http2 += http2_size
        total_http2_no_path += http2_no_path_size

    num = len(args.http_header_files)

    logging.info("Summary")
    print("Average HTTP/1.1 header size: %.0f bytes" % (total_http1 / num))
    print("Average HTTP/2 header size: %.0f bytes" % (total_http2 / num))
    print("Average HTTP/2 header size excluding :path: %.0f bytes" % (total_http2_no_path / num))
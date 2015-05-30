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

    tests = ("http1", "http2", "http2_no_path", "k_push_5", "k_push_inf")
    encoders = {k: hpack.Encoder() for k in tests if k != "http1"}
    total = {k: 0 for k in tests}

    for i, filename in enumerate(args.http_header_files):
        logging.info(filename)
        size, headers = read_headers(filename)

        total["http1"] += size
        logging.info("Header size for headers %s in HTTP/1.1: %s bytes" % (i, size))

        encoded_headers = [encoders["http2"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        size = sum(map(len, encoded_headers)) + HTTP2_FRAME_OVERHEAD
        total["http2"] += size
        logging.info("Header size for headers %s in HTTP/2: %s bytes" % (i, size))

        encoded_headers = [encoders["http2_no_path"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers
                           if key != ":path"]
        size = sum(map(len, encoded_headers)) + HTTP2_FRAME_OVERHEAD
        total["http2_no_path"] += size
        logging.info("Header size for headers %s excluding :path in HTTP/2: %s bytes" % (i, size))

        if i % 5 == 0:
            encoded_headers = [encoders["k_push_5"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                               for key, value in headers]
            size = sum(map(len, encoded_headers)) + HTTP2_FRAME_OVERHEAD
            total["k_push_5"] += size
            logging.info("Header size for headers %s in HTTP/2 + K-Push (K=5): %s bytes" % (i, size))
            if i == 0:
                total["k_push_inf"] = size
                logging.info("Header size for headers %s excluding :path in HTTP/2 + K-Push (K=inf): %s bytes" % (i, size))

        logging.info("")

    num = len(args.http_header_files)

    logging.info("Summary")
    print("HTTP/1.1 header size: %s bytes total, %.0f bytes average" % (total["http1"], total["http1"] / num))
    print("HTTP/2 header size: %s bytes total, %.0f bytes average" % (total["http2"], total["http2"] / num))
    print("HTTP/2 header size excluding :path: %s bytes total, %.0f bytes average" % (total["http2_no_path"], total["http2_no_path"] / num))
    print("HTTP/2 header size using K-Push (K=5): %s bytes total, %.0f bytes average" % (total["k_push_5"], total["k_push_5"] / num))
    print("HTTP/2 header size using K-Push (K=infinity): %s bytes total, %.0f bytes average" % (total["k_push_inf"], total["k_push_inf"] / num))
#!/usr/bin/env python3
import argparse
from hpack import hpack
import json
import logging
import os
import random
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


HTTP2_FRAME_OVERHEAD = 9 # See HTTP/2 section 4.1: Frame Format
HTTP2_HEADERS_OVERHEAD = 1 # See HTTP/2 section 6.1: DATA
HTTP2_REQUEST_OVERHEAD = HTTP2_FRAME_OVERHEAD * 2 + HTTP2_HEADERS_OVERHEAD
WEBSOCKET_FRAME_OVERHEAD = 4 # See FDH section 8.2.2: Frame Format and Semantics


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


def headers_as_utf8(headers):
    return [(key.encode("UTF-8"), value.encode("UTF-8"))
            for key, value in headers]

class Test(object):
    def __init__(self, description):
        self.description = description
        self.total = 0
        self.num = 0

    def print_size(self, size):
        logging.info("Header size for headers in %s: %s bytes" % (self.description, size))

    def print_total(self):
        print("%s: %s bytes total, %.0f bytes average" % \
            (self.description, self.total, self.total / self.num))


class HTTP1Test(Test):
    def encode(self, header):
        self.num += 1
        encoded = ["%s %s HTTP/1.1" % (headers[0][1], headers[1][1])]
        for key, value in headers[2:]:
            encoded.append("%s: %s" % (key, value))
        encoded.append("")
        size = len("\r\n".join(encoded))
        self.total += size
        self.print_size(size)


class HTTP2Test(Test):
    def __init__(self, description, k=None):
        super().__init__(description)
        self.encoder = hpack.Encoder()
        self.k = k

    def encode(self, headers):
        self.num += 1
        if self.k is not None:
            if self.k == 0:
                if self.num != 1:
                    return
            elif (self.num - 1) % self.k != 0:
                return
            headers = headers[:]
            headers.append(("DASH-PUSH", "type=push-next,params=K:%s" % self.k))
        encoded = self.encoder.encode(headers_as_utf8(headers))
        size = len(encoded) + HTTP2_REQUEST_OVERHEAD
        self.total += size
        self.print_size(size)


class HTTP2TestNoPath(HTTP2Test):
    def encode(self, headers):
        super().encode([(key, value) for key, value in headers if key != ":path"])


class WebSocketTest(Test):
    def __init__(self, description, k):
        super().__init__(description)
        self.k = k

    def encode(self, headers):
        self.num += 1
        if self.k is not None:
            if self.k == 0:
                if self.num != 1:
                    return
            elif (self.num - 1) % self.k != 0:
                return
        data = {
            "PushType": "push-next",
            "PushParams": "K:%s" % self.k,
            "URL": path # Should this be fully-qualified?
        }
        size = len(json.dumps(data)) + WEBSOCKET_FRAME_OVERHEAD
        self.total += size
        self.print_size(size)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("http_header_files", nargs="+")
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO if args.verbose else logging.WARNING)

    tests = [
        HTTP1Test("HTTP/1"),
        HTTP2Test("HTTP/2"),
        HTTP2TestNoPath("HTTP/2 excluding :path"),
        HTTP2Test("HTTP/2 + K-Push (K=5)", k=5),
        HTTP2Test("HTTP/2 + K-Push (K=infinity)", k=0),
        WebSocketTest("FDH WebSocket (K=1)", k=1),
        WebSocketTest("FDH WebSocket (K=5)", k=5),
        WebSocketTest("FDH WebSocket (K=infinity)", k=0)
    ]

    for i, filename in enumerate(args.http_header_files):
        logging.info(filename)
        size, headers = read_headers(filename)
        path = headers[1][1]

        for test in tests:
            test.encode(headers)

        logging.info("")

    num = len(args.http_header_files)

    logging.info("Summary")
    for test in tests:
        test.print_total()
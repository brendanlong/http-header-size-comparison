#!/usr/bin/env python3
import argparse
import glob
from hpack import hpack
import json
import logging
import math
import os
import random
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs


HTTP2_FRAME_OVERHEAD = 9 # See HTTP/2 section 4.1: Frame Format
HTTP2_HEADERS_OVERHEAD = 1 # See HTTP/2 section 6.1: DATA
HTTP2_REQUEST_OVERHEAD = HTTP2_FRAME_OVERHEAD * 2 + HTTP2_HEADERS_OVERHEAD
MAXIMUM_PACKET_SIZE = 1500 # Ethernet
MINIMUM_ACK_SIZE = 40
WEBSOCKET_FRAME_OVERHEAD = 4 # See FDH section 8.2.2: Frame Format and Semantics


def list_files(pattern):
    files = glob.glob(pattern)
    files.sort()
    return files


def read_headers(filename):
    headers = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if not line:
                break
            if not headers:
                method, path, _ = line.split(" ")
                headers.append((":method", method))
                headers.append((":path", path))
            else:
                headers.append([v.strip() for v in line.split(":", maxsplit=1)])
    return headers


def read_content_length(filename):
    with open(filename) as f:
        for line in f:
            if line.lower().startswith("content-length"):
                return int(line.split(":", maxsplit=1)[1])


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

    def print_total(self, ack):
        print("%s: %s bytes total, %.0f bytes average (%.0f bytes with ACK)" % \
            (self.description, self.total, self.total / self.num, ack + (self.total / self.num)))


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
    def __init__(self, description, k=None, literal_path=False):
        super().__init__(description)
        self.encoder = hpack.Encoder()
        self.k = k
        self.literal_path = literal_path

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
        encoded = []
        for key, value in headers_as_utf8(headers):
            if self.literal_path and key == b":path":
                encoded.extend(self.encoder._encode_literal(key, value, False, huffman=True))
            else:
                encoded.extend(self.encoder.add((key, value), huffman=True))
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
            "URL": headers[1][1] # Should this be fully-qualified?
        }
        size = len(json.dumps(data)) + WEBSOCKET_FRAME_OVERHEAD
        self.total += size
        self.print_size(size)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("request_files", help="Pattern for header files. Example: req.*.txt")
    parser.add_argument("response_files", help="Pattern for header files. Example: res.*.txt")
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO if args.verbose else logging.WARNING)

    tests = [
        HTTP1Test("HTTP/1"),
        HTTP2Test("HTTP/2"),
        HTTP2Test("HTTP/2 with literal :path", literal_path=True),
        HTTP2TestNoPath("HTTP/2 excluding :path"),
        HTTP2Test("HTTP/2 + K-Push (K=5)", k=5),
        HTTP2Test("HTTP/2 + K-Push (K=infinity)", k=0),
        #HTTP2Test("HTTP/2 + K-Push and literal :path (K=5)", k=5, literal_path=True),
        #HTTP2Test("HTTP/2 + K-Push and literal :path (K=infinity)", k=0, literal_path=True),
        WebSocketTest("FDH WebSocket (K=1)", k=1),
        WebSocketTest("FDH WebSocket (K=5)", k=5),
        WebSocketTest("FDH WebSocket (K=infinity)", k=0)
    ]

    ack_total = 0
    n = 0
    for i, (request, response) in enumerate(zip(list_files(args.request_files), list_files(args.response_files))):
        logging.info("%s - %s", request, response)

        headers = read_headers(request)
        for test in tests:
            test.encode(headers)

        content_size = read_content_length(response)
        num_packets = content_size / MAXIMUM_PACKET_SIZE
        num_acks = math.ceil(num_packets / 2)
        ack_size = num_acks * MINIMUM_ACK_SIZE
        ack_total += ack_size
        logging.info("Sending %.0f bytes requires %.0f packets, %s 40-byte acks, or %.0f bytes of acks" % \
            (content_size, num_packets, num_acks, ack_size))

        logging.info("")
        n += 1

    logging.info("Summary")
    for test in tests:
        test.print_total(ack_total / n)
    print("TCP ACK packets: %.0f bytes total, %.0f bytes average" % (ack_total, ack_total / n))
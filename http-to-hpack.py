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

    tests = ("http1", "http2", "http2_no_path", "k_push_5", "k_push_inf", "websocket_k_1",
        "websocket_k_5", "websocket_k_inf")
    encoders = {k: hpack.Encoder() for k in tests if k != "http1" and not k.startswith("websocket")}
    total = {k: 0 for k in tests}

    for i, filename in enumerate(args.http_header_files):
        logging.info(filename)
        size, headers = read_headers(filename)
        path = headers[1][1]

        # HTTP/1.1
        total["http1"] += size
        logging.info("Header size for headers %s in HTTP/1.1: %s bytes" % (i, size))

        # HTTP/2
        encoded_headers = [encoders["http2"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers]
        size = sum(map(len, encoded_headers)) + HTTP2_REQUEST_OVERHEAD
        total["http2"] += size
        logging.info("Header size for headers %s in HTTP/2: %s bytes" % (i, size))

        # HTTP/2 no :path
        encoded_headers = [encoders["http2_no_path"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                           for key, value in headers
                           if key != ":path"]
        size = sum(map(len, encoded_headers)) + HTTP2_REQUEST_OVERHEAD
        total["http2_no_path"] += size
        logging.info("Header size for headers %s excluding :path in HTTP/2: %s bytes" % (i, size))

        # WebSocket (K=1)
        data = {
            "PushType": "push-next",
            "PushParams": "K:1",
            "URL": path # Should this be fully-qualified?
        }
        size = len(json.dumps(data)) + WEBSOCKET_FRAME_OVERHEAD
        total["websocket_k_1"] += size
        logging.info("Frame size for headers %s in FDH WebSocket (K=1): %s bytes" % (i, size))

        if i % 5 == 0:
            # HTTP/2 + K-Push (K=5)
            encoded_headers = [encoders["k_push_5"].add((key.encode("UTF-8"), value.encode("UTF-8")))
                               for key, value in headers]
            encoded_headers.append(encoders["k_push_5"].add((b"DASH-PUSH", b"type=push-next,params=K:5")))
            size = sum(map(len, encoded_headers)) + HTTP2_REQUEST_OVERHEAD
            total["k_push_5"] += size
            logging.info("Header size for headers %s in HTTP/2 + K-Push (K=5): %s bytes" % (i, size))
            if i == 0:
                # HTTP/2 + K-Push (K=infinity)
                total["k_push_inf"] = size
                logging.info("Header size for headers %s excluding :path in HTTP/2 + K-Push (K=inf): %s bytes" % (i, size))

            # WebSocket (K=5)
            data = {
                "PushType": "push-next",
                "PushParams": "K:5",
                "URL": path # Should this be fully-qualified?
            }
            size = len(json.dumps(data)) + WEBSOCKET_FRAME_OVERHEAD
            total["websocket_k_5"] += size
            logging.info("Frame size for headers %s in FDH WebSocket (K=5): %s bytes" % (i, size))
            if i == 0:
                # WebSocket (K=infinity)
                total["websocket_k_inf"] = size
                logging.info("Frame size for headers %s in FDB WebSocket (K=inf): %s bytes" % (i, size))

        logging.info("")

    num = len(args.http_header_files)

    logging.info("Summary")
    print("HTTP/1.1 header size: %s bytes total, %.0f bytes average" % (total["http1"], total["http1"] / num))
    print("HTTP/2 header size: %s bytes total, %.0f bytes average" % (total["http2"], total["http2"] / num))
    print("HTTP/2 header size excluding :path: %s bytes total, %.0f bytes average" % (total["http2_no_path"], total["http2_no_path"] / num))
    print("HTTP/2 header size using K-Push (K=5): %s bytes total, %.0f bytes average" % (total["k_push_5"], total["k_push_5"] / num))
    print("HTTP/2 header size using K-Push (K=infinity): %s bytes total, %.0f bytes average" % (total["k_push_inf"], total["k_push_inf"] / num))
    print("WebSocket frame size (K=1): %s bytes total, %.0f bytes average" % (total["websocket_k_1"], total["websocket_k_1"] / num))
    print("WebSocket frame size (K=5): %s bytes total, %.0f bytes average" % (total["websocket_k_5"], total["websocket_k_5"] / num))
    print("WebSocket frame size (K=infinity): %s bytes total, %.0f bytes average" % (total["websocket_k_inf"], total["websocket_k_inf"] / num))
# HTTP Header Size Comparison

This tool reads HTTP/1.1 requests, then converts them to various protocols (HTTP/2, HTTP/2 + K-Push, MPEG DASH-FDH WebSocket protocol) and compares the byte overhead of each. It also reads the content length from the corresponding HTTP response and calculates the minimum size of the TCP ACK packets.

## Usage

    ./http-to-hpack.py "example-data/youtube/req.*" "example-data/youtube/res.*"

Note that the request and response files are given as a shell glob, not individual arguments.

The requests and responses need to be in ASCIIbetical order so be aware that res.10.txt comes before res.2.txt. Use file names like res.01.txt to handle that.

For details of each request, add the `-v` argument.

## Example Output

	$ ./http-to-hpack.py -v "example-data/youtube/req.*" "example-data/youtube/res.*"
	example-data/youtube/req.01.txt - example-data/youtube/res.01.txt
	Header size for headers in HTTP/1: 1285 bytes
	Header size for headers in HTTP/2: 971 bytes
	Header size for headers in HTTP/2 with literal :path: 976 bytes
	Header size for headers in HTTP/2 excluding :path: 351 bytes
	Header size for headers in HTTP/2 + K-Push (K=5): 1001 bytes
	Header size for headers in HTTP/2 + K-Push (K=infinity): 1001 bytes
	Header size for headers in FDH WebSocket (K=1): 897 bytes
	Header size for headers in FDH WebSocket (K=5): 897 bytes
	Header size for headers in FDH WebSocket (K=infinity): 897 bytes
	Sending 342 bytes requires 0 packets, 0 40-byte acks, or 5 bytes of acks

	[ etc. ]

	example-data/youtube/req.10.txt - example-data/youtube/res.10.txt
	Header size for headers in HTTP/1: 1316 bytes
	Header size for headers in HTTP/2: 700 bytes
	Header size for headers in HTTP/2 with literal :path: 677 bytes
	Header size for headers in HTTP/2 excluding :path: 29 bytes
	Header size for headers in FDH WebSocket (K=1): 928 bytes
	Sending 1330933 bytes requires 887 packets, 444 40-byte acks, or 17746 bytes of acks

	Summary
	HTTP/1: 13115 bytes total, 1312 bytes average (13064 bytes with ACK)
	HTTP/2: 7676 bytes total, 768 bytes average (12520 bytes with ACK)
	HTTP/2 with literal :path: 7084 bytes total, 708 bytes average (12461 bytes with ACK)
	HTTP/2 excluding :path: 637 bytes total, 64 bytes average (11816 bytes with ACK)
	HTTP/2 + K-Push (K=5): 1699 bytes total, 170 bytes average (11922 bytes with ACK)
	HTTP/2 + K-Push (K=infinity): 1001 bytes total, 100 bytes average (11852 bytes with ACK)
	FDH WebSocket (K=1): 9235 bytes total, 924 bytes average (12676 bytes with ACK)
	FDH WebSocket (K=5): 1825 bytes total, 182 bytes average (11935 bytes with ACK)
	FDH WebSocket (K=infinity): 897 bytes total, 90 bytes average (11842 bytes with ACK)
	TCP ACK packets: 117522 bytes total, 11752 bytes average
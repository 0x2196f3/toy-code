import argparse
import base64
import os
import socket
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)


class AuthSimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    secret_key = None

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="File Server"')
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Unauthorized")

    def check_auth(self):
        if not self.secret_key:
            return True

        auth_header = self.headers.get("Authorization")
        if auth_header is None:
            return False

        try:
            auth_type, encoded = auth_header.split(" ", 1)
            if auth_type.lower() != "basic":
                return False
            decoded = base64.b64decode(encoded).decode("utf-8")
            _, password = decoded.split(":", 1)
            return password == self.secret_key
        except Exception:
            return False

    def do_GET(self):
        if not self.check_auth():
            self.do_AUTHHEAD()
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.check_auth():
            self.do_AUTHHEAD()
            return
        super().do_HEAD()

    def do_POST(self):
        if not self.check_auth():
            self.do_AUTHHEAD()
            return
        super().do_POST()


def get_local_ips():
    ip_list = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ip_list.append(ip)
    except Exception:
        pass
    return ip_list


def main():
    parser = argparse.ArgumentParser(
        description="Simple Single-File HTTP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--listen",
        "-l",
        default="0.0.0.0:8000",
        help="Listen IP and port, format IP:PORT (default: 0.0.0.0:8000)",
    )
    parser.add_argument(
        "--secret",
        "-s",
        default=None,
        help="Optional password (default: None)",
    )
    parser.add_argument(
        "--root",
        "-r",
        default=".",
        help="Root directory (default: script directory)",
    )

    args = parser.parse_args()

    listen_str = args.listen
    if ":" in listen_str:
        host, port_str = listen_str.rsplit(":", 1)
        port = int(port_str)
    else:
        host = "0.0.0.0"
        port = int(listen_str)

    root_dir = os.path.abspath(args.root)
    if not os.path.exists(root_dir):
        print(f"Error: Specified root directory does not exist: {root_dir}")
        sys.exit(1)

    AuthSimpleHTTPRequestHandler.secret_key = args.secret

    handler_class = partial(AuthSimpleHTTPRequestHandler, directory=root_dir)

    try:
        server = HTTPServer((host, port), handler_class)
    except Exception as e:
        print(f"Failed to start server: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

    print("=" * 60)
    print(" HTTP File Server Started")
    print("=" * 60)
    print(f" Root directory: {root_dir}")
    print(
        f" Password protection: {'Enabled (Basic Auth)' if args.secret else 'Disabled'}"
    )
    print(f" Bound address: {host}:{port}")
    print("-" * 60)
    print(" Available addresses:")
    print(f"   - Local: http://127.0.0.1:{port}/")

    local_ips = get_local_ips()
    for ip in local_ips:
        print(f"   - LAN:   http://{ip}:{port}/")

    print("=" * 60)
    print("Press Ctrl+C to stop the server\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    main()
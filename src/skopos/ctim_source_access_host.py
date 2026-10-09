"""Canal Unix local para leer las siete fuentes CTIM fijadas por el host."""

import argparse
import json
import os
import signal
import socket
import socketserver
import stat

from skopos.ctim_source_access import AccessGateway, AccessError, _canonical


MAX_REQUEST = 4096
MAX_RESPONSE = 256 * 1024


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(15)
            raw = self.rfile.readline(MAX_REQUEST + 1)
            if not raw or len(raw) > MAX_REQUEST or not raw.endswith(b'\n'):
                raise AccessError('invalid_request')
            request = json.loads(raw)
            response = self.server.gateway.handle(request)
        except (AccessError, ValueError, UnicodeError, OSError):
            response = {'schema': 'skopos/ctim-source-access/v0.1',
                        'status': 'invalid_input', 'result': None,
                        'error': {'code': 'invalid_request', 'stage': 'validation'}}
        try:
            self.wfile.write(_canonical(response) + b'\n')
        except OSError:
            pass


def host_command(argv=None):
    parser = argparse.ArgumentParser(prog='skopos ctim-source-access')
    sub = parser.add_subparsers(dest='mode', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--policy', required=True)
    request = sub.add_parser('request')
    request.add_argument('--socket', required=True)
    request.add_argument('--request-file', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'request':
        try:
            with open(args.request_file, 'rb') as stream:
                raw = stream.read(MAX_REQUEST + 1)
            if not raw or len(raw) > MAX_REQUEST:
                raise OSError('request_size')
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(30)
                connection.connect(args.socket)
                connection.sendall(raw.rstrip(b'\n') + b'\n')
                with connection.makefile('rb') as stream:
                    reply = stream.readline(MAX_RESPONSE + 1)
            if not reply or len(reply) > MAX_RESPONSE:
                raise OSError('response_size')
            response = json.loads(reply)
        except (OSError, ValueError, UnicodeError):
            response = {'schema': 'skopos/ctim-source-access/v0.1',
                        'status': 'execution_failed', 'result': None,
                        'error': {'code': 'host_unavailable', 'stage': 'transport'}}
        print(json.dumps(response, ensure_ascii=False))
        return 0 if response.get('status') == 'ok' else 1

    gateway = AccessGateway(args.policy)
    socket_path = gateway.policy['socket_path']
    try:
        with socketserver.UnixStreamServer(socket_path, _Handler) as server:
            server.gateway = gateway
            os.chmod(socket_path, 0o600)
            details = os.lstat(socket_path)
            previous = signal.getsignal(signal.SIGTERM)

            def terminate(_number, _frame):
                raise SystemExit(0)

            signal.signal(signal.SIGTERM, terminate)
            try:
                server.serve_forever()
            finally:
                signal.signal(signal.SIGTERM, previous)
                try:
                    current = os.lstat(socket_path)
                    if (stat.S_ISSOCK(current.st_mode)
                            and (current.st_dev, current.st_ino) ==
                            (details.st_dev, details.st_ino)):
                        os.unlink(socket_path)
                except FileNotFoundError:
                    pass
    finally:
        gateway.close()
    return 0

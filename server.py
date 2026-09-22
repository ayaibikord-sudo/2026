import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

os.chdir('/home/user/2026')

class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

def run_port(port):
    try:
        server = HTTPServer(('0.0.0.0', port), PreviewHandler)
        print(f'Server listening on 0.0.0.0:{port}', flush=True)
        server.serve_forever()
    except Exception as e:
        print(f'Port {port} error: {e}', flush=True)

if __name__ == '__main__':
    for p in [3000, 8000]:
        t = threading.Thread(target=run_port, args=(p,), daemon=True)
        t.start()
    run_port(8080)

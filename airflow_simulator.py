#!/usr/bin/env python3
import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class AirflowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "simulator": true}')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html><body>
            <h1>Airflow Simulator</h1>
            <p>This is a simulated Airflow instance for development.</p>
            <p>Status: Running</p>
            </body></html>
            ''')
    
    def log_message(self, format, *args):
        return  # Suppress logs

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 8080), AirflowHandler)
    print("Airflow Simulator listening on port 8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Airflow simulator...")
        server.shutdown()

#!/usr/bin/env python3
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

class KafkaUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/actuator/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "UP", "kafka": "simulation"}')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html><body>
            <h1>Kafka UI Simulator</h1>
            <p>Visual interface for Kafka cluster management</p>
            <p>Cluster: okr-kafka-cluster (KRaft mode)</p>
            <p>Topics: okr-objectives, okr-key-results, okr-updates, okr-notifications, okr-analytics</p>
            <p>Status: Running in simulation mode</p>
            </body></html>
            ''')
    
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 8090), KafkaUIHandler)
    print("Kafka UI Simulator listening on port 8090")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Kafka UI simulator...")
        server.shutdown()

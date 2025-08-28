#!/usr/bin/env python3
import socket
import threading
import time
import json
from datetime import datetime

class KafkaSimulator:
    def __init__(self, port=9092):
        self.port = port
        self.running = False
        self.messages = []
        
    def start(self):
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            print(f"Kafka Simulator listening on port {self.port}")
            
            while self.running:
                try:
                    client_socket, addr = server_socket.accept()
                    print(f"Connection from {addr}")
                    # Simple response to simulate Kafka
                    response = b"Kafka simulator running\n"
                    client_socket.send(response)
                    client_socket.close()
                except:
                    pass
        except Exception as e:
            print(f"Error starting Kafka simulator: {e}")
        finally:
            server_socket.close()
            
    def stop(self):
        self.running = False

if __name__ == "__main__":
    simulator = KafkaSimulator()
    try:
        simulator.start()
    except KeyboardInterrupt:
        print("Stopping Kafka simulator...")
        simulator.stop()

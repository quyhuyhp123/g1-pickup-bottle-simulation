"""Acknowledged simulation commands; independent of policy observations/actions."""

import zmq


class SimulationControlChannel:
    def __init__(self, port=5581, bind=False):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.IMMEDIATE, 1)
        endpoint = f"tcp://127.0.0.1:{port}"
        if bind:
            self.socket.bind(endpoint)
        else:
            self.socket.connect(endpoint)

    def send(self, message):
        try:
            self.socket.send_json(message, zmq.NOBLOCK)
            return True
        except zmq.Again:
            return False

    def receive(self):
        try:
            return self.socket.recv_json(zmq.NOBLOCK)
        except zmq.Again:
            return None

    def close(self):
        self.socket.close()
        self.context.term()

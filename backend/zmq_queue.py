from collections import deque
import zmq
import time

from logger import log


# TODO: use IPC with a pipe instead of TCP

# Basically these two classes connect two deques via ZMQ:
# deque -> ZMQ -> deque
# threads working on boths deques continously move data from the deque on the server to the deque on the client


class ZMQQueueServer(object):
    def __init__(self, host='*', port=10000):
        self._host = host
        self._port = port
        self._deque = deque()

    def __len__(self):
        return len(self._deque)

    def run(self):
        log.info('Starting ZMQQueueServer')
        self._connect(self._host, self._port)
        while True:
            # wait for data
            # TODO proper sleep time
            while not self._deque:
                time.sleep(0.1)
            header, payload = self._deque.popleft()
            self._socket.send_json(header, flags=zmq.SNDMORE)
            self._socket.send(payload)

    def put(self, item):
        self._deque.append(item)

    def _connect(self, host, port):
        context = zmq.Context()
        self._socket = context.socket(zmq.PUSH)
        uri = 'tcp://{0}:{1:d}'.format(host, port)
        self._socket.bind(uri)
        log.info('ZMQQueueServer: Bound to ' + uri)


class ZMQQueueClient(object):
    def __init__(self, host='localhost', port=10000):
        self._host = host
        self._port = port
        self._deque = deque()
        self._connect(self._host, self._port)

    def __len__(self):
        return len(self._deque)

    def run(self):
        log.info('Starting ZMQQueueClient')
        while True:
            header = self._socket.recv_json()
            payload = self._socket.recv()
            self._deque.append((header, payload))

    def get(self):
        while not self._deque:
            time.sleep(0.1)
        return self._deque.popleft()

    def _connect(self, host, port):
        context = zmq.Context()
        self._socket = context.socket(zmq.PULL)
        uri = 'tcp://{0}:{1:d}'.format(host, port)
        self._socket.connect(uri)
        log.info('ZMQQueueClient: Connected to ZMQQueueServer at ' + uri)

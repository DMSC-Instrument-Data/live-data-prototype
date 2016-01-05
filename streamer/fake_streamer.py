import zmq

import ports
from logger import log


class FakeEventStreamer(object):
    def __init__(self, eventGenerator, version=1):
        self.version = version
        self.socket = None
        self.eventGenerator = eventGenerator

    def connect(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.PUSH)
        uri = 'tcp://*:{0:d}'.format(ports.event_stream)
        self.socket.bind(uri)
        log.info('Bound to {}'.format(uri))

    def _send_meta_data(self, meta_data):
        header = self._create_meta_data_header()
        self.socket.send_json(header, flags=zmq.SNDMORE)
        self.socket.send_json(meta_data)

    def _send_event_data(self, event_data):
        header = self._create_event_data_header()
        self.socket.send_json(header, flags=zmq.SNDMORE)
        self.socket.send(event_data)

    def _create_basic_header(self, packet_type):
        header = {
                'version':self.version,
                'type':packet_type,
                }
        return header

    def _create_event_data_header(self):
        header = self._create_basic_header('event_data')
        header['record_type'] = self.eventGenerator.get_type_info()
        return header

    def _create_meta_data_header(self):
        header = self._create_basic_header('meta_data')
        return header

    def run(self):
        log.info('Starting FakeEventStreamer...')
        self.connect()

        while True:
            # we first send all meta data for a pulse, then all event data
            self._send_meta_data(self.eventGenerator.get_meta_data())
            self._send_event_data(self.eventGenerator.get_events())

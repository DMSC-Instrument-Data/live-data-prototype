import threading
import time
import numpy
import zmq
from mpi4py import MPI

import ports
import command_line_parser
import mantid_reduction
import mantid_reducer
from parameter_control_server import ParameterControlServer
from distributed_parameter_control_server import DistributedParameterControlServer
from result_publisher import ResultPublisher


comm = MPI.COMM_WORLD

print 'Rank {0:3d} started.'.format(comm.Get_rank())


class EventListener(threading.Thread):
    def __init__(self, mantidReducer):
        threading.Thread.__init__(self)
        self.daemon = True
        self.data = None
        self.result = None
        self.bin_boundaries = None
        self.bin_values = None
        self.resultLock = threading.Lock()
        self.context = None
        self.socket = None
        self._mantidReducer = mantidReducer

    def run(self):
        print 'Starting EventListener...'
        self.connect()
        self.get_stream_info()
        while True:
            data = self.get_data_from_stream()
            split_data = self.distribute_stream(data)
            self.process_data(split_data)
            #processed_data = self.process_data(split_data)
            #gathered_data = self.gather_data(processed_data)
            #self.update_result(gathered_data)

    def connect(self):
        if comm.Get_rank() == 0:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REQ)
            uri = 'tcp://{0}:{1:d}'.format(command_line_parser.get_host(), ports.event_stream)
            self.socket.connect(uri)
            print 'Connected to event streamer at ' + uri

    def get_stream_info(self):
        if comm.Get_rank() == 0:
            self.socket.send('h')
            info = self.socket.recv_json()
            self.record_type = info['record_type']

    def get_data_from_stream(self):
        if comm.Get_rank() == 0:
            self.socket.send('d')
            header = self.socket.recv_json()
            event_count = header['event_count']
            data = self.socket.recv()
            return numpy.frombuffer(data, dtype=self.record_type)
        else:
            return None

    def distribute_stream(self, data):
        if comm.Get_rank() == 0:
            split = []
            for i in range(comm.size):
                split.append([])
            for i in data:
                detector_id = int(i[0])
                target = detector_id % comm.size
                split[target].append(i)
        else:
            split = None
        return comm.scatter(split, root=0)

    #def process_data(self, data):
    #    return mantid_reduction.reduce(data)

    def process_data(self, data):
        self._mantidReducer.reduce(data)

    def gather_data(self, data):
        rawdata = comm.gather(data[1], root=0)
        if comm.Get_rank() == 0:
            summed = sum(rawdata)
            return data[0], summed

    def update_result(self, data):
        if comm.Get_rank() == 0:
            self.resultLock.acquire()
            if self.bin_boundaries == None:
                self.bin_boundaries = numpy.array(data[0], copy=True)
                self.bin_values = numpy.array(data[1], copy=True)
            else:
                self.bin_values += data[1]
            self.resultLock.release()


if __name__ == '__main__':
    mantidReducer = mantid_reducer.MantidReducer()

    mantidRebinner = mantid_reducer.MantidRebinner()
    mantidRebinner.start()

    # TODO: MPI...
    #binController = ParameterControlServer(port=ports.rebin_control, parameter_dict=mantidRebinner.get_parameter_dict())
    binController = DistributedParameterControlServer(port=ports.rebin_control, parameter_dict=mantidRebinner.get_parameter_dict())
    binController.start()

    mantidMerger = mantid_reducer.MantidMerger(mantidReducer, mantidRebinner)
    mantidMerger.start()

    eventListener = EventListener(mantidReducer)
    eventListener.start()

    if comm.Get_rank() == 0:
        #resultPublisher = ResultPublisher(eventListener)
        resultPublisher = ResultPublisher(mantidRebinner)
        resultPublisher_thread = threading.Thread(target=resultPublisher.run)
        resultPublisher_thread.start()
        parameterController = ParameterControlServer(port=ports.result_publisher_control, parameter_dict=resultPublisher.get_parameter_dict())
        parameterController.start()

    while threading.active_count() > 0:
        time.sleep(0.1)

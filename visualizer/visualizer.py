from collections import deque
import zmq
import sys
import numpy
import PyQt4
import mantid.simpleapi as simpleapi
import mantidqtpython as mpy
import random
from logger import log
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
ConfigService = simpleapi.ConfigService


class InstrumentView(object):
    def __init__(self, dataListener):
        self.dataListener = dataListener
	ws = simpleapi.CreateSimulationWorkspace(Instrument='data/POWDIFF_Definition.xml', BinParams='1,0.5,2')
	self._number_of_spectra = ws.getNumberHistograms()
	ws = simpleapi.WorkspaceFactory.Instance().create("Workspace2D", self._number_of_spectra, 2, 1)
	simpleapi.AnalysisDataService.Instance().addOrReplace('POWDIFF_test', ws)
	simpleapi.LoadInstrument(Workspace=ws, Filename='data/POWDIFF_Definition.xml', RewriteSpectraMap=True)
	ws = simpleapi.Rebin(ws, "0,5,10")
	simpleapi.AnalysisDataService.Instance().addOrReplace('POWDIFF_test', ws)
        ws.getAxis(0).setUnit('tof')
	
	InstrumentWidget = mpy.MantidQt.MantidWidgets.InstrumentWidget
        self.iw = InstrumentWidget('POWDIFF_test')
        self.iw.show()

    def clear(self):
        ws = simpleapi.AnalysisDataService['POWDIFF_test']
	#could either delete workspace and go through the __init__ again or clear the data individually?	

    def updateInstrumentView(self):
	ws = simpleapi.AnalysisDataService['POWDIFF_test']
	simpleapi.AnalysisDataService.Instance().addOrReplace('POWDIFF_test', ws)
        while self.dataListener.data:
            data = self.dataListener.data.popleft()
	    index = 0
	    for packet in numpy.array_split(data, 1000):
	    	x, y, e = numpy.array_split(packet, 3)
	    	ws.dataY(index)[1] = y[0] #is 2
	    	ws.dataE(index)[1] = e[0]
	    	ws.dataX(index)[0] = x[0]
	    	ws.dataX(index)[1] = x[1]
	    	ws.dataX(index)[2] = x[2]
	   	index+=1
	   
class Plotter(object):
    def __init__(self, dataListener):
        self.dataListener = dataListener
        self.win = pg.GraphicsWindow()
        self.win.resize(800,350)
        self.win.setWindowTitle('pyqtgraph example: Histogram')
        self.plt1 = self.win.addPlot()
        self.curves = {}

    def clear(self):
        self.curves = {}
        self.plt1.clear()

    def update(self):
        while self.dataListener.data:
            index,x,y = self.dataListener.data.popleft()
            if not index in self.curves:
                self.curves[index] = self.plt1.plot(stepMode=True, pen=(index), name=str(index))
            self.curves[index].setData(x, y)
        self.plt1.enableAutoRange('xy', False)

class DataListener(PyQt4.QtCore.QObject):
    clear = PyQt4.QtCore.pyqtSignal()
    new_data = PyQt4.QtCore.pyqtSignal()

    def __init__(self, host, port):
        PyQt4.QtCore.QObject.__init__(self)
        self.data = deque()
        self._host = host
        self._port = port

    def run(self):
        log.info('Starting DataListener...')
        self.connect()
        while True:
            command, index = self._receive_header()
            if command == 'instrumentData':
	        data = numpy.frombuffer(self.socket.recv(), numpy.float64)
                self.data.append((data))
                self.new_data.emit()
	    if command == 'graphData':
		x,y = self.get_histogram()
                self.data.append((index,x,y))
                self.new_data.emit()
            elif command == 'clear':
                self.clear.emit()

    def connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        uri = 'tcp://{0}:{1:d}'.format(self._host, self._port)
        self.socket.connect(uri)
        self.socket.setsockopt(zmq.SUBSCRIBE, '')
        log.info('Subscribed to result publisher at ' + uri)

    def get_histogram(self):
        data = numpy.frombuffer(self.socket.recv(), numpy.float64)
        x,y = numpy.array_split(data, 2)
        return x,y	

    def _receive_header(self):
        header = self.socket.recv_json()
        command = header['command']
        index = header['index']
        return command, index

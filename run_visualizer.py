from threading import Thread

from pyqtgraph.Qt import QtGui

from logger import setup_global_logger
import ports
import command_line_parser
from visualizer import DataListener
from visualizer import Plotter


setup_global_logger(level=command_line_parser.get_log_level())

data_listener = DataListener(host=command_line_parser.get_host(), port=ports.result_stream)
data_listener_thread = Thread(target=data_listener.run)
data_listener_thread.daemon = True
plotter = Plotter(data_listener)

data_listener.clear.connect(plotter.clear)
data_listener.new_data.connect(plotter.update)
data_listener_thread.start()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-H", "--host", type=str, default='localhost', help='Host to connect to.')
parser.add_argument("-l", "--log", type=str, default='info', help="Set the log level. Allowed values are 'critical', 'error', 'warning', 'info', and 'debug'.")
args = parser.parse_args()

def get_host():
    return args.host

def get_log_level():
    return args.log

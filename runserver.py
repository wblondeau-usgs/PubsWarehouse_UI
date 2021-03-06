import argparse
from pubs_ui import app as application


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-ht', type=str)
    args = parser.parse_args()
    host_val = args.host
    if host_val is not None:
        host = host_val
    else:
        host = '127.0.0.1'
    application.run(host=host, port=5050)
    # run from the command line as follows
    # python runserver.py -ht <ip address of your choice>
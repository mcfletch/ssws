"""Synchronous API for external server-side processes

The *messaging server* should never use these interfaces,
they are intended for Django and similar processes which 
want to write a message to a channel and/or add/remove 
sessions to/from a channel.
"""
import os, sys
import argparse
from . import base

class Channel(base.Channel):
    pass

class Session(base.Session):
    def add_readable(self, channel_id):
        filename = os.path.join(self.readable_path, channel_id)
        with open(filename, 'w') as fh:
            fh.write('flag-file')
    def remove_readable(self, channel_id):
        filename = os.path.join(self.readable_path, channel_id)
        try:
            os.remove(filename)
            return True 
        except Exception:
            return False
    def add_writable(self, channel_id):
        filename = os.path.join(self.writable_path, channel_id)
        with open(filename, 'w') as fh:
            fh.write('flag-file')
    def remove_writable(self, channel_id):
        filename = os.path.join(self.writable_path, channel_id)
        try:
            os.remove(filename)
            return True 
        except Exception:
            return False
    def can_write(self, channel_id):
        return os.path.exists(os.path.join(self.writable_path, channel_id))
    def can_read(self, channel_id):
        return os.path.exists(os.path.join(self.readable_path, channel_id))

class Server(base.Server):
    """Synchronous API for the server"""
    SESSION_CLASS = Session 
    CHANNEL_CLASS = Channel


def alnum_string(input):
    if not base.simple_id(input):
        raise argparse.ArgumentTypeError("Need a value with only chars in [a-zA-Z0-9-]", input)
    return input
def alnum_string_or_empty(input):
    if not input:
        return input 
    return alnum_string(input)

parser = argparse.ArgumentParser(description='Do server-side ssws configuration from scripts/command lines')
parser.add_argument('session', metavar='SESSION', type=alnum_string,
                   help='Session being manipulated')
parser.add_argument('--channel', metavar='CHANNEL',action='append', type=alnum_string_or_empty,
                    dest='channels', 
                   help='Channel to be manipulated (argument can be repeated)')
parser.add_argument('--writable', dest='writable', action='store_const',
                   const=True, default=False,
                   help='Allow the session to write to the given channel')
parser.add_argument('--readable', dest='readable', action='store_const',
                   const=True, default=False,
                   help='Allow the session to write to the given channel')
parser.add_argument('--no-writable', dest='writable', action='store_const',
                   const=False, default=False,
                   help='Do not allow the session to write to the given channel')
parser.add_argument('--no-readable', dest='readable', action='store_const',
                   const=False, default=False,
                   help='Do not allow the session to write to the given channel')
parser.add_argument('--remove', dest='remove', action='store_const',
                   const=True, default=False,
                   help='Cleanup/de-register this session')

def session_main():
    arguments = parser.parse_args()
    server = Server()
    session = server.session(arguments.session)
    if arguments.remove:
        session.cleanup()
    elif not arguments.channels:
        # just letting them connect so far...
        pass
    else:
        if arguments.writable:
            for channel in arguments.channels:
                session.add_writable(channel)
        else:
            for channel in arguments.channels:
                session.remove_writable(channel)
        if arguments.readable:
            for channel in arguments.channels:
                session.add_readable(channel)
        else:
            for channel in arguments.channels:
                session.remove_readable(channel)

mparser = argparse.ArgumentParser(description='Do server-side ssws configuration from scripts/command lines')
mparser.add_argument('channel', metavar='CHANNEL', type=alnum_string,
                   help='Channel to which to send message')
mparser.add_argument('--message', dest='message', default=None,
                   help='Pass the message in as an argument, otherwise use stdin')


def message_main():
    arguments = mparser.parse_args()
    if not arguments.message:
        message = sys.stdin.read()
    else:
        message = arguments.message
    server = Server()
    channel = server.channel(arguments.channel)
    channel.write(message)
    

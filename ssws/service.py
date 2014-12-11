"""Messaging server service using Twisted and txws
"""
import os, json, sys, time
from . import base
from twisted.internet import inotify
from twisted.python import filepath, log
from twisted.application import strports
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import txws

class Channel(base.Channel):
    def __init__(self, *args, **named):
        super(Channel, self).__init__(*args, **named)
        log.msg("Channel %r started"%( self.channel_id, ))
    
    def setup(self):
        super(Channel, self).setup()
        for path, cb in [
            (self.outbox_path, self.on_outbox_message), 
        ]:
            self.server.inotify.watch(
                filepath.FilePath(path), callbacks=[cb]
            )
        
    def cleanup(self):
        log.msg("Removing channel: %r"%( self.channel_id, ))
        for path in (self.outbox_path, ):
            try:
                self.server.inotify.ignore(filepath.FilePath(path))
            except KeyError:
                pass
        super(Channel, self).cleanup()
    def on_outbox_message(self, _, path, mask ):
        if mask & inotify.IN_CREATE or mask & inotify.IN_MOVED_TO:
            # do some os hardlinks...
            # this should likely be async, but we rely on in-memory fs to be fast
            for session in self.server.sessions.values():
                if self.channel_id in session.readable:
                    session.add_message(path.path)
            os.unlink(path.path)
            self.mark_active()

class Session(base.Session):
    def __init__(self, *args, **named):
        self.readable = set()
        self.writable = set()
        self.outgoing_queue = []
        self.protocols = []
        super(Session, self).__init__(*args, **named)
    
    def setup(self):
        super(Session, self).setup()
        for path, cb in [
            (self.readable_path, self.on_readable_change), 
            (self.writable_path, self.on_writable_change), 
        ]:
            self.server.inotify.watch(
                filepath.FilePath(path), callbacks=[cb]
            )
        # load any existing setup...
        self.outgoing_queue[:] = [x[0] for x in base._ordered_ls(self.outbox_path)]
        # readable/writable
        for channel in os.listdir(self.readable_path):
            self.readable.add(channel)
        for channel in os.listdir(self.writable_path):
            self.writable.add(channel)
    def cleanup(self):
        for protocol in self.protocols:
            protocol.transport.loseConnection()
        for path in (self.readable_path, self.writable_path):
            try:
                self.server.inotify.ignore(filepath.FilePath(path))
            except KeyError:
                pass
        super(Session, self).cleanup()
    
    def on_readable_change(self, _, path, mask ):
        base = os.path.basename(path.path)
        if mask & inotify.IN_CREATE or mask & inotify.IN_MOVED_TO or mask:
            log.msg('Granting read to %s on %s'%(self.session_id, base))
            self.mark_active()
            self.readable.add(base)
        elif mask & inotify.IN_DELETE:
            log.msg('Revoking read from %s on %s'%(self.session_id, base))
            self.readable.remove(base)
    def on_writable_change(self, _, path, mask ):
        base = os.path.basename(path.path)
        if mask & inotify.IN_CREATE or mask & inotify.IN_MOVED_TO or mask:
            log.msg('Granting write to %s on %s'%(self.session_id, base))
            self.mark_active()
            self.writable.add(base)
        elif mask & inotify.IN_DELETE:
            log.msg('Revoking write from %s on %s'%(self.session_id, base))
            self.writable.remove(base)
    
    def add_message(self, filename):
        """Hardlink filename into our message queue"""
        target = os.path.join(self.outbox_path, os.path.basename(filename))
        os.link(filename, target )
        self.outgoing_queue.append(target)
        self.send_pending()
    def retire_message(self, filename):
        """Retire message after it has been sent"""
        # we sent a message (or tried, at least)
        self.mark_active()
        try:
            self.outgoing_queue.remove(filename)
        except ValueError:
            pass
        try:
            os.unlink(filename)
            return True
        except Exception:
            return False
    def on_incoming(self, channel_id, data):
        assert base.simple_id(channel_id)
        if channel_id in self.writable:
            self.mark_active()
            self.server.channel(channel_id).write(data)
            return True 
        else:
            log.err("Attempted write to unauth channel %r by %r"%( channel_id, self.session_id, ))
        return False
    def send_pending(self):
        """Called when we may have something to send..."""
        to_send = self.outgoing_queue[:]
        del self.outgoing_queue[:len(to_send)]
        send_to = [protocol for protocol in self.protocols if protocol.ready]
        if send_to:
            for message in to_send:
                with open(message, 'rb') as fh:
                    content = fh.read()
                for protocol in send_to:
                    protocol.add_message(content)
                    # duh, this should wait until all protocols have sent it or 
                    # errored out, not have the first one retire the message!
                self.retire_message(message)
            for protocol in send_to:
                reactor.callLater(0, protocol.send_pending)

class Server(base.Server):
    """Twisted API for the server"""
    SESSION_CLASS = Session 
    CHANNEL_CLASS = Channel
    def __init__(self, *args, **named):
        self.channels = {}
        self.sessions = {}
        super(Server, self).__init__(*args, **named)
    def setup(self):
        super(Server, self).setup()
        self.inotify = inotify.INotify()
        self.inotify.startReading()
        for path, cb in [
            (self.sessions_path, self.on_sessions_change), 
            (self.channels_path, self.on_channels_change), 
        ]:
            assert os.path.exists(path)
            self.inotify.watch(
                filepath.FilePath(path), callbacks=[cb]
            )
        for channel_id in os.listdir(self.channels_path):
            self.channel(channel_id, create=True)
        for session_id in os.listdir(self.sessions_path):
            self.session(session_id, create=True)
        self.reaping_loop = LoopingCall(self.reaper)
        self.reaping_loop.start(120.0)
    def cleanup(self):
        for path in (self.sessions_path, self.channels_path):
            try:
                self.server.inotify.ignore(filepath.FilePath(path))
            except KeyError:
                pass
        super(Server, self).cleanup()
        self.reaping_loop.stop()
        
    def session(self, session_id, create=True):
        current = self.sessions.get(session_id)
        if (current is None) and create:
            current = super(Server, self).session(session_id)
            self.sessions[session_id] = current 
        return current 
    def channel(self, channel_id, create=True):
        current = self.channels.get(channel_id)
        if (current is None) and create:
            current = super(Server, self).channel(channel_id)
            self.channels[channel_id] = current 
        return current 

    def on_channels_change(self, _, path, mask ):
        channel_id = os.path.basename(path.path)
        if mask & inotify.IN_CREATE or mask & inotify.IN_MOVED_TO or mask:
            self.channel(channel_id)
        elif mask & inotify.IN_DELETE:
            channel = self.channel(channel_id)
            channel.cleanup()
    def on_sessions_change(self, _, path, mask):
        session_id = os.path.basename(path.path)
        if mask & inotify.IN_CREATE or mask & inotify.IN_MOVED_TO or mask:
            self.session(session_id)
        elif mask & inotify.IN_DELETE:
            session = self.session(session_id)
            session.cleanup()
            try:
                del self.sessions[session_id]
            except KeyError:
                pass
    
    REAPING_FREQUENCY = 60*2
    SESSION_TIMEOUT = 60*60*4
    def reaper(self):
        current =  time.time()
        stale = current - self.SESSION_TIMEOUT
        
        for session_id, session in self.sessions.items():
            last = session.last_active()
            if last < stale:
                if not session.protocols:
                    log.msg('Clearing out session: %s'%(session_id))
                    session.cleanup()
                else:
                    log.msg('Session %s is inactive, but has connections'%(session_id, ))
        for channel_id, channel in self.channels.items():
            last = channel.last_active()
            if last < stale:
                log.msg('Clearing out channel: %s'%(channel_id))
                channel.cleanup()
    
from twisted.internet.protocol import Protocol, Factory
class SSWSProtocol(Protocol):
    ready = False
    def __init__(self, *args, **named):
        self.outgoing_queue = []
    def add_message(self, message):
        self.outgoing_queue.append(message)
    def write_error(self, message, channel=''):
        self.transport.write('%s,%s'%(channel, json.dumps({'error':True, 'message':message})))
    def write_welcome(self, channel=''):
        self.transport.write('%s,{"success":true,"message":"Connection established"}'%(channel, ))
    def dataReceived(self, data):
        if self.transport.protocol.state == txws.FRAMES:
            if not self._session:
                session_id = self.transport.protocol.location.lstrip('/')
                if not base.simple_id(session_id):
                    log.err("Invalid Session ID: %r"%( session_id, ))
                    self.write_error("session invalid")
                    self.transport.loseConnection()
                    return
                log.msg("New Connection on Session: %r"%( session_id, ))
                session = self.factory.server.session(session_id, create=False)
                if not session:
                    log.err("Unkown/no-auth session: %r"%( session_id, ))
                    self.write_error("session unknown")
                    self.transport.loseConnection()
                    return
                self._session = session
                self._session.protocols.append(self)
                self.write_welcome()
            else:
                session = self._session
            try:
                channel_id, data = data.split(',', 1)
            except ValueError:
                log.error('Mis-formatted request (no ,)')
                self.write_error('Missing comma in request')
                return 
            if not channel_id:
                """Protocol-level messages, currently nothing"""
                pass 
            elif not base.simple_id(channel_id):
                log.err("Invalid Channel ID: %r"%( channel_id, ))
                self.write_error("invalid channel")
                self.transport.loseConnection()
                return
            else:
                session.on_incoming(channel_id, data)
            self.ready = True
    _session = None
    def connectionLost(self, reason):
        self.ready = False
        try:
            self._session.protocols.remove(self)
        except (AttributeError, ValueError):
            pass 
    def send_pending(self):
        if not self.transport.protocol.state == txws.FRAMES:
            return 
        while self.outgoing_queue:
            message = self.outgoing_queue.pop()
            self.transport.write(message)

class SSWSFactory(Factory):
    protocol = SSWSProtocol
    def __init__(self, server, *args, **named ):
        self.server = server 

import argparse
parser = argparse.ArgumentParser(description='SSWS Back-end server (intended to be run behind an nginx proxy in production)')
parser.add_argument(
    '-d','--directory', 
    metavar='DIRECTORY', 
    default = '/run/shm/ssws', 
    help='SSWS spooling directory, SHOULD be stored in a RAM disk'
)
def valid_strport(value):
    try:
        strports.parse( value, default='tcp:5775' )
    except (ValueError, KeyError) as err:
        raise argparse.ArgumentTypeError(*err.args)
    return value 
parser.add_argument(
    '-l','--listen', 
    metavar='STRPORT', 
    default = 'tcp:5775', 
    help='Specification of the listening interface in twisted.application.strports format, e.g. tcp:5900 or unix:/tmp/listening.sock', 
)
parser.add_argument(
    '--log', 
    metavar='FILENAME', 
    default=None, 
    help='If specified, log to the given log-file instead of stdout', 
)


def main():
    arguments = parser.parse_args()
    if arguments.log:
        log.startLogging(open(arguments.log, 'w'))
    else:
        log.startLogging(sys.stderr)
    server = Server(base_path=arguments.directory)
    strports.listen(arguments.listen, txws.WebSocketFactory(SSWSFactory(server)))
    reactor.run()

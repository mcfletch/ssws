"""Web Socket/Twisted based messaging server

Intended for use behind an nginx server providing SSL
termination and providing a session-key which will be
validated *before* the session is sent to us. This is 
*not* a generic message queuing system, it's intended 
to allow for "server sent events" and basic chat 
type services.

Basic Operation:

* The server sends messages to given channels
* The server adds channels to sessions
* We assume an inbox model running in a tempfs or 
  similar in-memory filesystem

Inbox Model:

    root path
        
        .tmp (writing directory)
        
        sessions
    
            session_id

                out
                
                readable
                    channel_id
                writable
                    channel_id
        
        channels
        
            channel_id
            
                out (outgoing messages)
                in (incoming messages)

When the server wants to initiate a message-send to channel:

    writes the data in .tmp
    
    moves the file into channels/<channel_id>/out
    
    the daemon's inotify on the channel/out hard-links the message 
    into each session's channel_id/out where the session has that 
    channel_id present. outgoing message-send is en-queued for the 
    session
    
    in the per-session outgoing operation, iterate through the 
    set of messages in the queue until there are no messages, for 
    each message, attempt to write to the socket, IFF we succeed and 
    get an ack, delete the message, otherwise retry when possible.
    

When the client wants to initiate a message-send to channel:

    sends websocket request
    
    on receipt, spools into .tmp
    
    reads channel from the request, decides whether the 
    channel is in writable. If it is, moves into channels/in
    
    IFF there's a handler registered for the channel, then 
    the daemon calls that handler. The most command handler is 
    going to be "broadcast" (move to out), so likely that 
    should be a special flag/common operation.
    
    Otherwise, the server is responsible for pulling messages 
    out of the in-box and deleting them when processed.
"""
import os, uuid, shutil, re

ID_MATCH = re.compile(r'^[-0-9a-zA-Z]+$')
simple_id = ID_MATCH.match

class Session(object):
    def __init__(self, server, session_id):
        self.server = server
        self.session_id = session_id
        self.session_path = server.session_path(session_id)
        self.setup()
    def setup(self):
        _ensure_dirs([self.outbox_path, self.readable_path, self.writable_path])
    
    @property
    def outbox_path(self):
        return os.path.join(self.session_path, 'out')
    @property
    def readable_path(self):
        return os.path.join(self.session_path, 'readable')
    @property
    def writable_path(self):
        return os.path.join(self.session_path, 'writable')
    
    def cleanup(self):
        shutil.rmtree(self.session_path)
    
class Channel(object):
    def __init__(self, server, channel_id):
        self.server = server 
        self.channel_id = channel_id
        self.channel_path = server.channel_path(channel_id)
        self.setup()
    def setup(self):
        _ensure_dirs([self.inbox_path, self.outbox_path])
    @property
    def inbox_path(self):
        return os.path.join(self.channel_path, 'in')
    @property
    def outbox_path(self):
        return os.path.join(self.channel_path, 'out')
    def write(self, message, inbox=False):
        """This is horribly synchronous"""
        guid = uuid.uuid4().hex
        filename = os.path.join(self.server.spool_dir, guid)
        if inbox:
            final = os.path.join(self.inbox_path, guid)
        else:
            final = os.path.join(self.outbox_path, guid)
        assert os.path.exists(self.server.spool_dir)
        try:
            with open(filename, 'wb') as fh:
                fh.write(message)
            os.rename(filename, final)
        except Exception as err:
            for fn in (filename, final):
                try:
                    os.remove(fn)
                except Exception:
                    pass 
            raise WriteError(str(err), message)
        return final
    def cleanup(self):
        shutil.rmtree(self.channel_path)

def _ensure_dirs(directories):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, 0775 )

def _ordered_ls(directory):
    """Do a timestamp-ordered directory listing of a directory"""
    def stats(filename):
        try:
            return os.stat(filename).st_ctime
        except Exception:
            return None
    filenames = [
        os.path.join(directory, f) for f in os.listdir(directory)
    ]
    return [
        (filename, mtime)
        for (filename, mtime) in [
            (filename, stats(filename))
            for filename in filenames
        ]
        if mtime is not None
    ]
    

class Server(object):
    """Server-side (synchronous API)"""
    SESSION_CLASS = Session 
    CHANNEL_CLASS = Channel
    def __init__(self, base_path='/run/shm/ssws'):
        self.base_path = base_path
        self.spool_dir = os.path.join(base_path, '.tmp')
        self.setup()
    def setup(self):
        _ensure_dirs([self.spool_dir, self.sessions_path, self.channels_path])
    @property
    def sessions_path(self):
        return os.path.join(self.base_path, 'session')
    @property
    def channels_path(self):
        return os.path.join(self.base_path, 'channel')
    def session_path(self, session_id):
        return os.path.join(self.base_path, 'session', session_id)
    def channel_path(self, channel_id):
        return os.path.join(self.base_path, 'channel', channel_id)
    def session(self, session_id):
        """Get a session object for the given id"""
        return self.SESSION_CLASS(self, session_id)
    def channel(self, channel_id):
        return self.CHANNEL_CLASS(self, channel_id)
    def cleanup(self):
        pass

class WriteError(IOError):
    """Raised if we can't write a message to the spool"""

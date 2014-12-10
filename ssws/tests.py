from unittest import TestCase
import os, shutil, tempfile
from . import sync, base

class BaseTests(TestCase):
    def setUp(self):
        self.temp_path = tempfile.mkdtemp(prefix='ssws-test-', dir='/run/shm')
        os.chmod(self.temp_path, 0775)
        self.server = sync.Server(self.temp_path)
    def tearDown(self):
        shutil.rmtree(self.temp_path, True)
        
    def test_session_setup(self):
        session = self.server.session('test')
        assert session.session_id == 'test'
        assert session.session_path.endswith('/test'), session.session_path
        assert os.path.exists( session.outbox_path )
        assert os.path.exists( session.readable_path )
        assert os.path.exists( session.writable_path )
    def test_session_readable(self):
        session = self.server.session('test')
        assert not session.can_read('moo')
        session.add_readable('moo')
        assert session.can_read('moo')
        session.remove_readable('moo')
        assert not session.can_read('moo')
    def test_session_writable(self):
        session = self.server.session('test')
        assert not session.can_write('moo')
        session.add_writable('moo')
        assert session.can_write('moo')
        session.remove_writable('moo')
        assert not session.can_write('moo')

    def test_channel_setup(self):
        channel = self.server.channel('moo')
        assert channel.channel_id == 'moo'
        assert channel.inbox_path.endswith('/moo/in')
        assert os.path.exists(channel.inbox_path)
        assert os.path.exists(channel.outbox_path)
    
    def test_channel_write(self):
        channel = self.server.channel('moo')
        filename = channel.write('Vladivostok')
        assert os.path.exists(filename)
        content = open(filename, 'rb').read()
        assert content == 'moo,Vladivostok', content
    
    def test_write_cleanup(self):
        channel = self.server.channel('moo')
        self.assertRaises(base.WriteError, channel.write, None)
        

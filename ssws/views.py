"""Trivial redirect view to be hooked into a django URL tree"""
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from annoying.decorators import render_to
import subprocess
from . import settings

try:
    from django.utils.module_loading import import_string
except ImportError:
    from django.utils.module_loading import import_by_path as import_string

def add_session(key, readable=(), writable=()):
    if not readable or writable:
        subprocess.check_call([
            'ssws-session', 
                key, 
        ])
    else:
        for set, flag in ((readable, '--readable'), (writable, '--writable')):
            items = []
            for item in set:
                items.extend(['--channel', item])
            subprocess.check_call([
                'ssws-session', 
                    flag, 
            ] + items + [ 
                    key, 
            ])
            
class WSRedirect(HttpResponseRedirect):
    allowed_schemes = ['ws', 'wss']

def default_callback(request):
    """Default enable callback, uses session_key for the session secret and enables 'default' channel read"""
    key = request.session.session_key
    add_session(
        key, 
        readable=settings.SETTINGS.get('default_readable'), 
        writable=settings.SETTINGS.get('default_writable'), 
    )
    return key

def _resolved(callback):
    if isinstance(callback, (bytes, unicode)):
        callback = import_string(callback)
    return callback
def _under_proxy(request):
    return request.META.get( settings.SETTINGS['proxy_test_header'] )
    
def _url_params(request, key=None):
    def base_host(host):
        if ']' in host:
            return host[:host.index(']')+1]
        else:
            return host.rsplit(':', 1)[0]
    host = request.get_host()
    params = {
        "session_key":key, 
        "host": host, 
        "host_base": base_host(host), 
        "server_port": settings.SETTINGS['server_port'], 
    }
    return params
def _redirect_url(request):
    if request.is_secure():
        protocol = 'wss'
    else:
        protocol = 'ws'
    params = _url_params(request)
    params['protocol'] = protocol
    base = '%(protocol)s://%(host)s'%params
    return base + reverse('ssws_redirect')

@login_required
def websocket_enable(
    request, 
    websocket_proxy_url=settings.SETTINGS['proxy_url_template'], 
    websocket_direct_url=settings.SETTINGS['direct_url_template'],  
    enable_callback = None, 
):
    """Perform ssws authentication (login checking)
    
    For a logged-in user:
    
        * sets up the ssws session permissions via enable_callback
          if not provided, .settings.SETTINGS['auth_callback'] is used 
        * redirects to either websocket_proxy_url or websocket_direct_url
          based on the presence of 
    if enable_callback is None then `default_callback` is used,
    which uses the django session_key as the secret key and 
    enables a single reading channel ('default').
    """
    if not enable_callback:
        enable_callback = _resolved(
            settings.SETTINGS.get('auth_callback') or default_callback
        )
    key = enable_callback( request )
    params = _url_params(request, key)
    # now need to get the request to go to the actual callback...
    if _under_proxy(request):
        relative = websocket_proxy_url%params
        response = HttpResponse( '' )
        response['X-Accel-Redirect'] = relative
        return response
    else:
        relative = websocket_direct_url % params
        return WSRedirect( relative )

@login_required
@render_to('ssws/chatsample.html')
def chat_sample(request):
    return {
        'redirect_url':_redirect_url(request), 
    }

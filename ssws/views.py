"""Trivial redirect view to be hooked into a django URL tree"""
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from annoying.decorators import render_to
import subprocess
from functools import wraps
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

def default_callback(request, read_channels, write_channels):
    """Default enable callback, uses session_key for the session secret and enables 'default' channel read"""
    key = request.session.session_key
    add_session(key, readable=read_channels, writable=write_channels)
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

def with_websocket_enable(
    read_channels=settings.SETTINGS['default_readable'], 
    write_channels=settings.SETTINGS['default_writable'], 
    enable_callback =settings.SETTINGS['auth_callback'], 
    websocket_proxy_url = settings.SETTINGS['proxy_url_template'], 
    websocket_direct_url=settings.SETTINGS['direct_url_template'],  
):
    """Wrap a request with ssws authorization setup...
    
    read_channels -- override the channels to grant read on for this view
    write_channels -- override the channels to grant write on for this view
    enable_callback -- a callable taking (request, read_channels, write_channels)
    websocket_proxy_url -- override URL to which to direct when running under nginx
    websocket_direct_url -- override URL to which to direct when running in dev mode
    """
    def with_websocket_decorator(function):
        @wraps(function)
        def with_websocket(request, *args,  **named):
            callback = _resolved( enable_callback )
            request.ssws_key = callback( request, read_channels, write_channels )
            params = _url_params(request, request.ssws_key)
            if _under_proxy(request):
                url = websocket_proxy_url%params
            else:
                url = websocket_direct_url % params
            request.ssws_url = url
            return function(request, *args,  **named)
        return with_websocket
    return with_websocket_decorator

@login_required
def proxy_redirector(request, proxy_redirect_template=settings.SETTINGS['proxy_redirect_template']):
    """Redirect on nginx incoming message to the internal websockets location"""
    # TODO: do we really want this to be parameterized, if so,
    # we should get this from settings and allow for overrides...
    key = request.session.session_key
    params = _url_params(request, key)
    url = proxy_redirect_template%params
    response = HttpResponse( '' )
    response['X-Accel-Redirect'] = url
    return response


@with_websocket_enable
@render_to('ssws/chatsample.html')
def chat_sample(request):
    return {
        'redirect_url':_redirect_url(request), 
    }

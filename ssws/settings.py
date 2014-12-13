"""Get our settings for our ssws server"""
from django.conf import settings

DEFAULT_SETTINGS = {
    # Callback to call to decide what channels a given request's session 
    # should have access to...
    'auth_callback':'ssws.views.default_callback', 
    # Default channels which are enabled for reading
    'default_readable':['default'], 
    # Default channels which are enabled for writing
    'default_writable':[],
    # Proxy URL template, i.e. how to get to the ssws server under nginx
    'proxy_url_template':'%(protocol)s://%(host)s/ws/%(session_key)s', 
    'proxy_redirect_template':'/ws-internal/%(session_key)s', 
    # Direct URL template, i.e. how to get to the ssws server in stand-alone/dev mode
    'direct_url_template':'%(protocol)s://%(host_base)s:%(server_port)s/ws/%(session_key)s', 
    'proxy_test_header': 'HTTP_X_NGINX_HOSTED', 
    'server_port': 5775, 
}

LOCAL_SETTINGS = getattr(settings, 'SSWS_CONFIG', {})
SETTINGS = DEFAULT_SETTINGS.copy()
SETTINGS.update(LOCAL_SETTINGS)

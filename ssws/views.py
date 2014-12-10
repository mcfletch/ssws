"""Trivial redirect view to be hooked into a django URL tree"""
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required

@login_required
def websocket_auth(
    request, 
    websocket_proxy_url='/ws/%(session_key)s', 
    websocket_direct_url='ws://%(host)s/%(session_key)s', 
):
    key = request.session.session_key
    if request.META.get( 'HTTP_X_NGINX_HOSTED' ):
        relative = websocket_proxy_url%{'session_key':key}
        response = HttpResponse( '' )
        response['X-Accel-Redirect'] = relative
        return response
    else:
        relative = websocket_direct_url % {
            "session_key":key, 
            "host": request.get_host(), 
        }
        return HttpResponseRedirect( relative )

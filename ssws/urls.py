from django.conf.urls import patterns, url

urlpatterns = patterns('ssws.views', 
    url(r'^/$', 'websocket_auth', name="ssws_redirect"), 
)

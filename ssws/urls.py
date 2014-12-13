from django.conf.urls import patterns, url

urlpatterns = patterns('ssws.views', 
    url(r'^/$', 'proxy_redirector', name="ssws_redirect"), 
)

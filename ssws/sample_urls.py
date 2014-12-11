from django.conf.urls import patterns, url

urlpatterns = patterns('ssws.views', 
    url(r'^/$', 'chat_sample', name="ssws_chat_sample"), 
)

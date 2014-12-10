# Server Driven Web Sockets Notifications

This server is a simplisitic (and small) piece of code 
intended for very small "embedded" deploys where a django
front-end is running on an appliance-style server and 
we would like to get websockets updates from server 
processes.

This is *not* a large scale messaging solution, nor is 
it intended to provide particularly robust messaging,
messages can (easily) be lost. The point is to allow 
for notifying a user when something big is happening 
rather than trying to create a messaging middleware.
The idea being that if they were to refresh they'd see 
the update anyway, this just lets them know there's 
a change *right now*.


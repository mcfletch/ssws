# Server Driven Web Sockets Notifications

This server is a simplisitic (and small) piece of code 
intended for very small "embedded" deploys where a django
front-end is running on an appliance-style server and 
we would like to get websockets updates from server 
processes.

# Operation in Development

Installation is done via pip:
```bash
$ virtualenv -p python2.7 ssws-testing
$ source ssws-testing/bin/activate
$ git clone https://github.com/mcfletch/ssws.git
$ cd ssws
$ python setup.py develop
```
You can play with the example by starting a web server in 
the `ssws/ssws/static/js` directory:
```bash
$ cd ssws/ssws/static/js
$ python -m "SimpleHttpServer" &
```
Open a web-browser and point it at http://localhost:8000/example.html
You will see a notice that the connection was refused.
Let's start the server and let the browser connect...
```bash
$ ssws-server &
```
Will start the server, your message in the browser should now say that 
the session is unknown. The server has to explicitly allow the session 
key to access the service, and further it has to allow reading 
(and writing) explicitly for each channel.
```bash
$ ssws-session --readable --channel default example-session
$ ssws-message --message "Hello World" default
```


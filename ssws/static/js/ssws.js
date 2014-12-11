;
(function ( $, window, document, undefined ) {
    $.ssws = function( config ) {
        var self = {
            uri: null,
            socket: null,
            ready: false,
            retry: true,
            retry_delay: .5,
            current_retry_delay: 0,
            
            pending_queue: [],
            events: {}
        };
        $.extend(self,config);
        self.get_socket = function() {
            if (self.socket) {
                return self.socket;
            } else if (self.uri) {
                self.socket = new WebSocket(self.uri);
                self.socket.onopen = self.on_open;
                self.socket.onclose = self.on_close;
                self.socket.onmessage = self.on_message;
                self.socket.onerror = self.on_error;
            } else {
                console.log('No WebSocket URI specified' );
            }
        };
        self.drain_queue = function() {
            var message;
            var socket = self.get_socket();
            while (self.pending_queue.length) {
                message = self.pending_queue.shift();
                socket.send(message);
            }
        };
        self.on_open = function(evt) {
            // Send a message over to the server
            self.current_retry_delay = self.retry_delay;
            self.ready = true;
            self.send("",'{}');
            self.drain_queue();
        };
        self.on_close = function(evt) {
            if (! evt.wasClean) {
                if (self.retry) {
                    self.retry_delay *= 1.25;
                    self.retry_delay = Math.min( self.retry_delay, 60 );
                    window.setTimeout( self.start, self.retry_delay * 1000 );
                }
            }
            self.ready = false;
            self.socket = null;
        };
        self.get_handler = function(channel) {
            // get the handler that should process messages from channel
            var operator = self.events[channel];
            if (operator !== undefined && operator !== null) {
                return operator;
            }
            if (channel) {
                return self.get_handler('');
            } else {
                return null;
            }
        };
        self.on_message = function(evt) {
            var split = evt.data.indexOf(',');
            if (split == -1) {
                console.log('Invalid message from server, no channel indicator'+event.data);
                return;
            }
            var channel = evt.data.substring(0,split);
            var data = evt.data.substring(split+1,evt.data.length);
            var operator = self.get_handler(channel);
            if (operator !== undefined && operator !== null) {
                try {
                    operator( channel, data );
                } catch (err) {
                    console.log('Err ' +err+ ' in handler for '+channel+' '+operator);
                }
            } else {
                console.log('Unregistered channel '+channel );
            }
        };
        self.on_error = function(evt) {
        };
        self.send = function( channel, content ) {
            if (self.ready) {
                self.get_socket().send( channel + ',' + content );
            } else {
                self.pending_queue.push( channel + ',' + content );
            }
        };
        self.start = function() {
            self.get_socket();
        };
        self.register = function(channel, callback) {
            // channel -- channel or '' for any unregistered channel 
            // callback -- callback, or null to clear the handler.
            self.events[channel] = callback;
        };
        return self;
    };
})( jQuery, window, document );

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
                if (self.socket.readyState === 0 || self.socket.readyState === 2 || self.socket.readyState === 3) {
                    // we are still connecting, have to wait or 
                    // we will retry after the closing finishes
                    return null;
                } else if (self.socket.readyState == 1 ) {
                    // ready to go...
                    return self.socket;
                } else if (self.socket.readyState == 0) {
                    return null;
                } else {
                    self.error_callback("Unrecognized readyState");
                }
            }
            if (self.uri) {
                try {
                    self.socket = new WebSocket(self.uri);
                } catch (err) {
                    self.error_callback('Connection failed '+err);
                    self.trigger_retry();
                    return null;
                }
                self.socket.onopen = self.on_open;
                self.socket.onclose = self.on_close;
                self.socket.onmessage = self.on_message;
                self.socket.onerror = self.on_error;
            } else {
                self.error_callback('No WebSocket URI specified');
            }
        };
        self.drain_queue = function() {
            var message;
            var socket = self.get_socket();
            if (socket && socket.readyState == 1) {
                while (self.pending_queue.length) {
                    message = self.pending_queue.shift();
                    socket.send(message);
                }
            }
        };
        self.on_open = function(evt) {
            // Send a message over to the server
            self.current_retry_delay = self.retry_delay;
            self.ready = true;
            if (self.pending_queue.length) {
                // we have things to send...
                self.drain_queue();
            } else {
                // trigger recognition on the server...
                self.socket.send(",{}");
            }
            self.error_callback('Connection established',false);
        };
        self.error_callback = function(message,error) {
            if (error === undefined || error === null) {
                error = true;
            }
            self.dispatch_message('',JSON.stringify({'error':true,'message':message}));
        };
        self.trigger_retry = function() {
            if (self.retry) {
                self.retry_delay *= 1.25;
                self.retry_delay = Math.min( self.retry_delay, 60 );
                window.setTimeout( self.start, self.retry_delay * 1000 );
            }
        };
        self.on_close = function(evt) {
            if (! evt.wasClean) {
                if (self.ready) {
                    self.error_callback('Connection lost ' + evt.code + ' ' + evt.reason);
                } else {
                    self.error_callback('Connection failed ' + evt.code + ' '+evt.reason);
                }
                self.trigger_retry();
            } else {
                self.error_callback('Connection closed',false);
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
                self.error_callback('Invalid message from server, no channel indicator'+event.data);
                return;
            }
            var channel = evt.data.substring(0,split);
            var data = evt.data.substring(split+1,evt.data.length);
            return self.dispatch_message(channel,data);
        };
        self.dispatch_message = function(channel,data) {
            var operator = self.get_handler(channel);
            if (operator !== undefined && operator !== null) {
                try {
                    operator( channel, data );
                } catch (err) {
                    console.log('Err ' +err+ ' in handler for '+channel+' '+operator);
                }
            } else {
                // Not necessarily a user-visible issue, as the session 
                // can be connected to lots of things that *this* page 
                // doesn't care about...
                console.log('Unregistered channel '+channel );
            }
        };
        self.on_error = function(evt) {
            self.error_callback(""+evt);
        };
        self.send = function( channel, content ) {
            self.pending_queue.push( channel + ',' + content );
            self.drain_queue();
        };
        self.start = function() {
            self.get_socket();
        };
        self.close = function() {
            if (self.socket) {
                self.drain_queue();
                self.socket.close(1000,'Orderly shutdown');
            }
        };
        self.register = function(channel, callback) {
            // channel -- channel or '' for any unregistered channel 
            // callback -- callback, or null to clear the handler.
            self.events[channel] = callback;
        };
        return self;
    };
})( jQuery, window, document );

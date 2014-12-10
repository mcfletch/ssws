;
(function ( $, window, document, undefined ) {
    $.ssws = function( config ) {
        var self = {
            uri: null,
            socket: null,
            reopen: true,
            retry_delay: 1,
            handlers: {}
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
        self.on_open = function(evt) {
            // Send a message over to the server
            self.send("",'{}');
        };
        self.on_close = function(evt) {
            if (self.reopen) {
                window.setTimeout( self.start, self.retry_delay * 1000 );
            }
            self.socket = null;
        };
        self.on_message = function(evt) {
        };
        self.on_error = function(evt) {
            
        };
        self.send = function( channel, content ) {
            self.get_socket().send( channel + ',' + content );
        };
        self.start = function() {
            self.get_socket();
        };
        self.register = function(channel, callback) {
            self.handlers[channel] = callback;
        };
        return self;
    };
})( jQuery, window, document );

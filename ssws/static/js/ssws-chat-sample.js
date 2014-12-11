$(document).ready( function() {
    $('.ssws').each(function() {
        var overall = $('.ssws');
        var status = overall.find('.status');
        var uri = overall.attr('data-ws-uri');
        var server = $.ssws({'uri':uri,'retry':true});
        server.register('',function( channel, message ) {
            var holder;
            overall.removeClass('error');
            if (channel) {
                holder = $('.channel .messages[data-channel='+channel+']');
            } else {
                var content = JSON.parse(message);
                if (content.error) {
                    overall.addClass('error');
                }
                if (content.message) {
                    var message = content.message;
                    if (message !== status.text()) {
                        status.text(message);
                    }
                }
                return;
            }
            if (!holder.length) {
                var wrapper = $('<div class="channel"><h2></h2><ul class="messages"></ul></div>');
                wrapper.find('h2').text(channel);
                holder = wrapper.find('.messages');
                holder.attr('data-channel',channel);
                overall.append(wrapper);
            }
            var new_message = $('<li><span class="message"></span></li>');
            new_message.find('.message').text(message);
            holder.append(new_message);
        });
        server.start();
    });
});

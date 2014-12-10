//upstream ws_server {
//   server http://localhost:5600 fail_timeout=0;
//}


// location /ws {
	// You must redirect from the main web-server to the websocket
	// so that you can authenticate the user first...
	internal;
	access_log off;
	proxy_set_header Host $host;
	proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Nginx-Hosted "Yes";
    proxy_set_header X-Forwarded-Protocol $scheme;

    # WebSocket support (nginx 1.4)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_pass http://ws_server;
	break;

// }

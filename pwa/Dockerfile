FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html  /usr/share/nginx/html/index.html
COPY manifest.json /usr/share/nginx/html/manifest.json
COPY sw.js       /usr/share/nginx/html/sw.js
COPY assets/     /usr/share/nginx/html/assets/

EXPOSE 80

FROM nginx:alpine

# nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Tüm site dosyaları
COPY index.html     /usr/share/nginx/html/index.html
COPY iletisim.html  /usr/share/nginx/html/iletisim.html
COPY indir.html     /usr/share/nginx/html/indir.html
COPY fiyat.html     /usr/share/nginx/html/fiyat.html
COPY sss.html       /usr/share/nginx/html/sss.html
COPY assets/        /usr/share/nginx/html/assets/

# Favicon kopyası (tarayıcı kök dizinden de arar)
RUN cp /usr/share/nginx/html/assets/img/favicon.png /usr/share/nginx/html/favicon.png

EXPOSE 80

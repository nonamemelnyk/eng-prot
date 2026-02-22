FROM nginx:alpine

COPY frontend/web/index.html frontend/web/styles.css frontend/web/app.js /usr/share/nginx/html/

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

FROM nginx:alpine

COPY frontend/web/index.html frontend/web/styles.css frontend/web/app.js frontend/web/config.js /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

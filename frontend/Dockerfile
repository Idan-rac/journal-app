FROM nginx:1.27-alpine

# Replace the default nginx site config with ours.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static frontend.
COPY index.html style.css app.js /usr/share/nginx/html/

EXPOSE 80

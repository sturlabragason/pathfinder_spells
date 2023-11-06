
# Use the Nginx Alpine image for a small footprint
FROM nginx:alpine

# Set the working directory to Nginx's serve directory
WORKDIR /usr/share/nginx/html

# Remove the default Nginx static files
RUN rm -rf ./*

# Copy the static content of the web application into the container
COPY index.html ./
COPY spells.js ./
COPY styles.css ./
COPY spells.tsv ./

# Expose port 80
EXPOSE 80

# Start Nginx and keep the process running
CMD ["nginx", "-g", "daemon off;"]

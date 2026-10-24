
# Use the Nginx Alpine image for a small footprint
FROM nginx:alpine

# Set the working directory to Nginx's serve directory
WORKDIR /usr/share/nginx/html

# Remove the default Nginx static files
RUN rm -rf ./*

# Copy the static content of the web application into the container
COPY index.html spells.js cards.js catalog.css spells.css spells.tsv ./
COPY fonts/ ./fonts/
COPY caladrel_ecthelion/ ./caladrel_ecthelion/

# Expose port 80
EXPOSE 80

# Start Nginx and keep the process running
CMD ["nginx", "-g", "daemon off;"]

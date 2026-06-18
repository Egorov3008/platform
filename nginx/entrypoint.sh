#!/bin/sh
set -e

# Render nginx template with BOT_SECRET_KEY env var.
# The whole /etc/nginx/conf.d/ is mounted :ro, so we cannot overwrite
# default.conf in place. We mount-overlay the file:
#   1. Copy all conf.d contents (including default.conf.template) to /tmp
#   2. Render template into /tmp/conf.d/default.conf
#   3. exec nginx with -c pointing to a master config that includes /tmp/conf.d

# Approach: nginx:alpine's main config is /etc/nginx/nginx.conf and
# includes everything from /etc/nginx/conf.d/*.conf. We replace that
# include path by bind-mounting /tmp/conf.d over /etc/nginx/conf.d
# for nginx. Bind mounts require root and runtime caps; simpler:
# write a master config that points the include to /tmp/conf.d.

# Step 1: render
mkdir -p /tmp/conf.d
cp /etc/nginx/conf.d/default.conf.template /tmp/conf.d/default.conf
envsubst '$BOT_SECRET_KEY' < /tmp/conf.d/default.conf > /tmp/conf.d/default.conf.tmp
mv /tmp/conf.d/default.conf.tmp /tmp/conf.d/default.conf
# Also copy any other files (certs, mime types, etc. — not used here, but safe)
cp -r /etc/nginx/conf.d/* /tmp/conf.d/ 2>/dev/null || true

# Step 2: build a master config that includes our /tmp/conf.d
cat > /tmp/nginx.conf <<NGINX
worker_processes 1;
error_log /dev/stderr warn;
pid /tmp/nginx.pid;
events { worker_connections 1024; }
http {
    include /tmp/conf.d/*.conf;
}
NGINX

# Step 3: exec
exec nginx -c /tmp/nginx.conf -g 'daemon off;'

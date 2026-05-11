#!/bin/sh
set -eu

FRAME_ANCESTORS_VALUE="${FRAME_ANCESTORS:-'self'}"
NGINX_CONF="${NGINX_CONF:-/etc/nginx/nginx.conf}"
ESCAPED_FRAME_ANCESTORS=$(printf '%s\n' "$FRAME_ANCESTORS_VALUE" | sed 's/[&|]/\\&/g')
TMP_CONF="${NGINX_CONF}.tmp"

sed "s|frame-ancestors 'self';|frame-ancestors ${ESCAPED_FRAME_ANCESTORS};|g" "$NGINX_CONF" > "$TMP_CONF"
cat "$TMP_CONF" > "$NGINX_CONF"
rm -f "$TMP_CONF"

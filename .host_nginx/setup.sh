#!/usr/bin/env bash
# Хостовая настройка публичного вебхука YooKassa на порту 8443.
# Запускать с root:  sudo bash /home/egorych/platform/.host_nginx/setup.sh
set -e

echo "[1/6] ufw: открыть 80 (ACME) и 8443 (вебхук)"
ufw allow 80/tcp   || true
ufw allow 8443/tcp || true

echo "[2/6] certbot: выпуск серта для tg-bot.tds-pro.space (HTTP-01, webroot /var/www/html)"
certbot certonly --webroot -w /var/www/html \
  -d tg-bot.tds-pro.space \
  --non-interactive --agree-tos --register-unsafely-without-email

echo "[3/6] установка nginx-конфига в /etc/nginx/conf.d/"
install -m 644 /home/egorych/platform/.host_nginx/tg-bot-webhook.conf \
  /etc/nginx/conf.d/tg-bot-webhook.conf

echo "[4/6] nginx -t"
nginx -t

echo "[5/6] start/restart nginx (стартует, если был выключен)"
systemctl restart nginx

echo "[6/6] проверка слушателя 8443"
ss -ltn | grep 8443 || true

echo "DONE"
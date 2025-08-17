
#!/usr/bin/env bash
set -e
sudo apt-get update -y
sudo apt-get install -y nginx
sudo cp deploy/nginx/mlapi.conf /etc/nginx/sites-available/mlapi
sudo ln -sf /etc/nginx/sites-available/mlapi /etc/nginx/sites-enabled/mlapi
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

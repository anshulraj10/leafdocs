# Deploying leafdocs

This covers taking `leafdocs` from `pip install` to a running production service on **AWS EC2** or **GCP Compute Engine**, reachable either by **raw IP** or by a **custom domain**. The stack is the same on both clouds: Gunicorn (WSGI) behind Nginx (reverse proxy), managed by systemd.

Two domain paths are included:
- **Path A — Direct + Certbot**: simplest, works when your instance has a public IPv4 and you're fine terminating TLS on the box itself.
- **Path B — Cloudflare Tunnel**: no public IPv4 required (works on IPv6-only instances), free SSL, WAF, and DNS. This is the setup actually running in production for this project.

---

## 1. Provision a VM

### AWS EC2

```bash
# Launch: Ubuntu 24.04 LTS (or Amazon Linux 2023), t4g.micro (arm64) or t3.micro
```

Security group — for **IP-only access**:

| Port | Protocol | Source |
|------|----------|--------|
| 22   | TCP | your IP (or 0.0.0.0/0 if you must) |
| 80   | TCP | 0.0.0.0/0, ::/0 |

Add **443** as well if you're doing Path A (Certbot terminates TLS on-box). For Path B (Cloudflare Tunnel), 443 inbound isn't needed — the tunnel is an outbound connection from the instance.

If you want a stable public IPv4, allocate an **Elastic IP** and associate it (costs ~$3.60/mo if the instance is stopped or you're not using the free tier's original quota — cheaper to skip this entirely if you're going the IPv6 + Tunnel route).

### GCP Compute Engine

```bash
gcloud compute instances create leafdocs-vm \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --machine-type=e2-micro \
  --zone=us-central1-a

gcloud compute firewall-rules create allow-http \
  --allow=tcp:80 --target-tags=http-server

gcloud compute firewall-rules create allow-https \
  --allow=tcp:443 --target-tags=http-server
```

Reserve a static external IP if you want IP access to stay stable across restarts:

```bash
gcloud compute addresses create leafdocs-ip --region=us-central1
```

SSH in either via `gcloud compute ssh leafdocs-vm` or a standard key-based SSH.

---

## 2. Install dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv nginx
```

## 3. Set up the app

```bash
mkdir ~/leafdocs-app && cd ~/leafdocs-app
python3 -m venv .venv
source .venv/bin/activate
pip install leafdocs gunicorn
mkdir docs   # your markdown files go here
```

`main.py`:

```python
from leafdocs import LeafDocs
from werkzeug.middleware.proxy_fix import ProxyFix

ld = LeafDocs(docs_dir="./docs")
app = ld.flask_app
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
```

`.env` (copy from `.env.example` in the repo):

```
LEAFDOCS_PINS=yourpin
LEAFDOCS_SECRET_KEY=your-long-random-secret-here
```

Generate the secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Sanity check:

```bash
gunicorn --bind 127.0.0.1:8000 main:app
```

## 4. systemd service

`/etc/systemd/system/leafdocs.service`:

```ini
[Unit]
Description=LeafDocs
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/leafdocs-app
EnvironmentFile=/home/ubuntu/leafdocs-app/.env
Environment="PATH=/home/ubuntu/leafdocs-app/.venv/bin"
ExecStart=/home/ubuntu/leafdocs-app/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now leafdocs
sudo systemctl status leafdocs
```

---

## 5. Access via raw IP (no domain)

Point Nginx at the app with a wildcard `server_name` so it responds on the instance's IP directly:

`/etc/nginx/sites-available/leafdocs`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/leafdocs /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Visit `http://<instance-ip>`. No HTTPS in this mode — fine for internal/testing use, not for anything pin-protected over an untrusted network (pins would go over plaintext HTTP).

---

## 6. Path A — Domain via direct DNS + Certbot

Point your domain's `A`/`AAAA` record at the instance's public IP, then:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot rewrites the Nginx config to add the 443/TLS block and sets up auto-renewal. Requires the instance to have a public IPv4 and ports 80+443 open.

---

## 7. Path B — Domain via Cloudflare Tunnel (no public IPv4 needed)

Use this if the instance is IPv6-only (cheaper on AWS — skips the Elastic IP charge) or you'd rather not expose the box directly to the internet.

Nginx stays **HTTP-only on port 80** — Cloudflare terminates SSL:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Install and authenticate `cloudflared`, then create a tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create leafdocs
cloudflared tunnel route dns leafdocs your-domain.com
```

`/etc/cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json
protocol: http2   # QUIC/UDP outbound is often blocked by cloud firewalls; force HTTP/2 over 443

ingress:
  - hostname: your-domain.com
    service: http://localhost:80
  - service: http_status:404
```

Run it as a service:

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

In Cloudflare DNS, the CNAME for `your-domain.com` is created automatically by `tunnel route dns`, proxied (orange-clouded). No inbound port 80/443 needs to be open on the cloud firewall/security group at all — the tunnel is outbound-only.

---

## Notes carried over from a production deployment

- **Small instances (1GB RAM or less)**: add a 1GB swapfile as a safety net —
  ```bash
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```
- **SSH hardening**: `MaxAuthTries 3`, `LoginGraceTime 20`, `PermitRootLogin no` in `/etc/ssh/sshd_config.d/hardening.conf`, plus `fail2ban`.
- **Backups**: nothing here is automated. Back up `docs/` (if not already synced from a git repo via CI) and both `.env` files before any destructive change.
- **IPv6-only quirks (AWS)**: GitHub over IPv6 can be flaky for `git clone`/push from the instance itself — clone elsewhere and `rsync`/`scp` docs over, or use a GitHub Actions + Tailscale deploy step instead of pulling directly on the box.
- **Cost**: an IPv6-only `t4g.micro` in `ap-south-1` with a Compute Savings Plan runs ~$7.50–8/mo, versus ~$15/mo for a `t3a.small` with an Elastic IP in `us-east-1` — region and instance family matter more than most people assume.
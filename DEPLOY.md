# Deploying the D20 Synth Workbench

Stack: one Linux host running Docker Compose with two containers.

| Container | Role |
|---|---|
| `app` | Node 22 + Express. Serves `V2/` (with the cloud UI injected), `/workbench` (`browser/`), `/instrument-library`, and the `/api` routes. SQLite at `/data/d20.db` (volume `app_data`). |
| `caddy` | Reverse proxy on 80/443. Automatic Let's Encrypt TLS via HTTP-01. |

DNS stays at GoDaddy; only an A record is needed.

## 1. Server

Minimum: 1 vCPU, 1 GB RAM, 20 GB disk, Ubuntu 24.04 LTS, static public IPv4.
Any of: GoDaddy VPS, AWS Lightsail / EC2, or another VPS.

Firewall / security group:

| Port | Source |
|---|---|
| 22/tcp | your IP only |
| 80/tcp | anywhere (ACME challenge + redirect) |
| 443/tcp, 443/udp | anywhere |

Install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out/in afterwards
```

## 2. Code and config

```bash
sudo mkdir -p /opt/d20 && sudo chown $USER /opt/d20
git clone -b fullstack https://github.com/mattehicks/Drum-Sequencer.git /opt/d20
cd /opt/d20/deploy
cp .env.example .env
sed -i "s/^SESSION_SECRET=.*/SESSION_SECRET=$(openssl rand -hex 32)/" .env
nano .env          # set DOMAIN and ACME_EMAIL (and GoDaddy keys if eligible)
chmod 600 .env
```

## 3. DNS (GoDaddy)

```bash
chmod +x godaddy-dns.sh backup.sh
./godaddy-dns.sh example.com drums        # subdomain drums.example.com
./godaddy-dns.sh example.com @            # or the apex
```

The script tries the GoDaddy API first. GoDaddy only grants DNS API access to accounts with 10+ domains or an active Discount Domain Club plan; otherwise it returns 401/403 and the script prints the exact A record to add in the GoDaddy DNS panel. It then polls public DNS until the name resolves to the server.

If GoDaddy shared cPanel hosting is the only option: the static app (`V2/index.html`, `V2/instrument-library/`) can be uploaded as-is and works without the backend; the cloud features need this Node server.

## 4. Start

Only after DNS resolves (Caddy needs it to obtain the certificate):

```bash
docker compose up -d --build
docker compose logs -f caddy     # watch for "certificate obtained successfully"
curl -s https://$DOMAIN/healthz  # {"ok":true}
```

## 5. Backups

```bash
crontab -e
15 3 * * * /opt/d20/deploy/backup.sh >> $HOME/d20-backup.log 2>&1
```

Snapshots go to `~/d20-backups` (14-day retention). Set `S3_BUCKET` in the crontab line's environment to also copy to S3 (needs the AWS CLI and credentials/instance role).

Restore:

```bash
docker compose stop app
gunzip -c ~/d20-backups/d20-<stamp>.db.gz > /tmp/restore.db
docker compose cp /tmp/restore.db app:/data/d20.db
docker compose start app
```

## 6. Updates

```bash
cd /opt/d20 && git pull && cd deploy && docker compose up -d --build
```

## Local development

```bash
cd server
npm install
NODE_ENV=development npm run dev          # http://localhost:8080
BASE=http://localhost:8080 npm test       # end-to-end API checks (server must be running)
```

Opening `V2/index.html` directly from disk still works; the cloud buttons only appear when it is served by this server.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | – | `{email, password}` → session cookie |
| POST | `/api/auth/login` | – | `{email, password}` → session cookie |
| POST | `/api/auth/logout` | – | clear cookie |
| GET | `/api/auth/me` | – | `{user}` or `{user:null}` |
| GET | `/api/projects` | yes | list (no data) |
| POST | `/api/projects` | yes | `{name?, data}` → `{id}` |
| GET/PUT/DELETE | `/api/projects/:id` | yes | read / replace / delete |
| POST/DELETE | `/api/projects/:id/share` | yes | create (`{slug}`) / revoke public link |
| GET | `/api/shared/:slug` | – | public read of a shared project |
| GET | `/api/kits` | – | instrument library index |
| GET | `/healthz` | – | liveness |

`data` must be a project object with `format: "d20-synth-project"` (what Save Project writes). Request bodies are limited to 10 MB. Sessions are HMAC-signed HttpOnly cookies valid 30 days; rotating `SESSION_SECRET` signs everyone out.

# UniGPU Deployment Guide: Oracle Cloud Always-Free

**Permanent Free Tier** (No credit card or expiration)

---

## Oracle Cloud Always-Free Resources Available

| Resource | Allocation | Cost |
|---|---|---|
| **Compute (ARM)** | 2 instances (4 OCPU, 24GB RAM total) OR 2× (1 OCPU, 1GB RAM) | Free |
| **Autonomous Database** | 20GB shared, 1 database | Free |
| **Object Storage** | 20GB | Free |
| **Load Balancer** | 1 with 10Mbps bandwidth | Free |
| **VCN (Networking)** | 2 VCNs | Free |
| **Data Transfer** | 10GB/month outbound | Free |

---

## Step 1: Oracle Cloud Account Setup

```bash
# 1. Create account at: https://www.oracle.com/cloud/free/
# 2. No credit card required for always-free tier
# 3. Verify email and complete identity verification

# After signup, you'll have:
# - Always-Free Compartment
# - Default VCN
```

---

## Step 2: Provision Resources

### A. Create Compute Instance (For Backend & Agent)

1. **Go to:** Compute → Instances
2. **Click:** "Create Instance"
3. **Configure:**
   - **Name:** `unigpu-backend`
   - **Image:** Ubuntu 22.04 LTS (Always-Free eligible)
   - **Shape:** Ampere A1 (Flexible) - **4 OCPU, 24GB RAM** (Free!)
   - **VCN:** Default VCN
   - **Public IP:** Assign (for SSH access)
   - **SSH Key:** Download and save `.key` file locally

4. **Click:** Create Instance
5. **Wait:** 2-3 minutes for startup

---

### B. Create Autonomous Database (PostgreSQL)

1. **Go to:** Oracle Database → Autonomous Database
2. **Click:** "Create Autonomous Database"
3. **Configure:**
   - **Display Name:** `unigpu-db`
   - **Database Name:** `unigpu`
   - **Workload Type:** Transaction Processing (OLTP)
   - **Database Version:** 23ai (or latest)
   - **CPU Core Count:** 1 (Free tier)
   - **Storage:** 20GB (Free tier)
   - **Admin Password:** Generate strong password, save it
   - **Network Access:** Allow Secure External Access
   - **License Type:** License Included

4. **Click:** Create Autonomous Database
5. **Wait:** 5-10 minutes for provisioning

6. **After created:**
   - Go to Database → Connection Strings
   - Copy **High** connection string (for asyncpg)
   - Example: `postgresql://admin:PASSWORD@abc123_high.adb.region.oraclecloud.com:1522/unigpu_high?ssl=true`

---

### C. Create Cache (For Redis - Optional, or use OCI Cache)

**Option 1:** Use OCI Cache (Managed Redis) - Free tier may be limited  
**Option 2:** Self-host Redis on Compute instance (Recommended for free tier)

For this guide, we'll **self-host Redis on the compute instance**.

---

## Step 3: SSH into Compute Instance

```bash
# 1. Download SSH key from Oracle (saved as unigpu_key.key)
# 2. Change permissions
chmod 600 unigpu_key.key

# 3. SSH into instance (replace with your public IP)
ssh -i unigpu_key.key ubuntu@your.instance.public.ip

# 4. Update system
sudo apt update && sudo apt upgrade -y
```

---

## Step 4: Install Docker & Dependencies

```bash
# On the compute instance:

# Install Docker
sudo apt install -y docker.io docker-compose

# Add user to docker group
sudo usermod -aG docker ubuntu

# Verify Docker
docker --version
docker-compose --version

# Install Git
sudo apt install -y git

# Clone your UniGPU repo
cd /home/ubuntu
git clone https://github.com/yourusername/UniGPU.git
cd UniGPU
```

---

## Step 5: Configure Environment Variables

Create `/home/ubuntu/UniGPU/backend/.env.prod`:

```bash
cat > backend/.env.prod << 'EOF'
# === ORACLE FREE TIER CONFIG ===

# Security
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Database (Autonomous DB connection string)
DATABASE_URL=postgresql+asyncpg://admin:YOUR_ADMIN_PASSWORD@abc123_high.adb.region.oraclecloud.com:1522/unigpu_high?ssl=true&sslmode=require

# Redis (Self-hosted on same instance)
REDIS_URL=redis://localhost:6379

# CORS (Set to your domain)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Billing
RATE_PER_SECOND=0.002

# Upload directory
UPLOAD_DIR=/mnt/storage/uploads

EOF
```

**Important:** Replace:
- `YOUR_ADMIN_PASSWORD` - Password set during DB creation
- `abc123_high.adb...` - Your actual DB connection string
- `yourdomain.com` - Your actual domain (get from Freenom or similar)

---

## Step 6: Install Redis on Compute Instance

```bash
# On the compute instance:

# Install Redis server
sudo apt install -y redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should return: PONG
```

---

## Step 7: Create Storage Directory

```bash
# Create uploads directory for job files
sudo mkdir -p /mnt/storage/uploads
sudo chown ubuntu:ubuntu /mnt/storage/uploads
chmod 755 /mnt/storage/uploads
```

---

## Step 8: Update docker-compose.prod.yml

Create a production-optimized compose file:

```yaml
# backend/docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build: .
    container_name: unigpu-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
    volumes:
      - /mnt/storage/uploads:/app/uploads
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    restart: always
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: unigpu-redis
    ports:
      - "6379:6379"
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

  celery-worker:
    build: .
    container_name: unigpu-celery
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - /mnt/storage/uploads:/app/uploads
    command: celery -A app.worker.celery_app worker -l info
    restart: always
    depends_on:
      - redis

volumes:
  redis-data:
```

---

## Step 9: Deploy Backend

```bash
# On the compute instance, from /home/ubuntu/UniGPU:

# Create .env file from .env.prod
cp backend/.env.prod backend/.env

# Build images
cd backend
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

---

## Step 10: Set Up Nginx Reverse Proxy (On Same Instance)

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx config
sudo cat > /etc/nginx/sites-available/unigpu << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend (React built files)
    location / {
        root /home/ubuntu/UniGPU/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/unigpu /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## Step 11: Set Up SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Step 12: Build & Deploy Frontend

```bash
# On your local machine (or in compute instance):

cd frontend

# Create .env.production
cat > .env.production << 'EOF'
VITE_API_BASE_URL=https://yourdomain.com/api
EOF

# Build
npm run build

# Copy to server
scp -r dist/* ubuntu@your.instance.ip:/home/ubuntu/UniGPU/frontend/dist/
```

Or from the compute instance:

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Build frontend
cd /home/ubuntu/UniGPU/frontend
npm install
npm run build
```

---

## Step 13: Configure Firewall (Security Group)

In Oracle Cloud Console:

1. **Go to:** Networking → Virtual Cloud Networks
2. **Select:** Default VCN
3. **Go to:** Security Lists → Default Security List
4. **Add Ingress Rules:**
   - **Port 22 (SSH):** Source 0.0.0.0/0 (or restrict to your IP)
   - **Port 80 (HTTP):** Source 0.0.0.0/0
   - **Port 443 (HTTPS):** Source 0.0.0.0/0
   - **Port 8000 (Backend):** Source VCN only (optional, for internal)

---

## Step 14: Verify Deployment

```bash
# Check services
docker ps

# Check logs
docker logs unigpu-backend
docker logs unigpu-celery

# Test API
curl https://yourdomain.com/api/

# Check Nginx
sudo systemctl status nginx

# Monitor system
free -h
df -h
```

---

## Step 15: Set Up Domain (Optional Free Domain)

**Free domain options:**
- **Freenom:** freenom.com (free .tk, .ml, .ga, .cf domains)
- **Cloudflare:** Free DNS with any domain
- **DuckDNS:** Free dynamic DNS

**Steps:**
1. Register domain on Freenom
2. Point DNS to your instance's public IP
3. Update Nginx config with actual domain
4. Get SSL certificate from Let's Encrypt

---

## Maintenance Tasks

### Daily Monitoring

```bash
# SSH into instance
ssh -i unigpu_key.key ubuntu@your.instance.public.ip

# Check disk space
df -h /mnt/storage

# Check database connection
sudo docker logs unigpu-backend | grep "database"

# Check Redis
redis-cli ping

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Backup Database

```bash
# Autonomous Database handles backups automatically
# Access backups in Oracle Console: Database → Backups
```

### Backup Application Data

```bash
# Backup uploads directory
tar -czf uploads-backup-$(date +%Y%m%d).tar.gz /mnt/storage/uploads/

# Copy to Object Storage (optional)
# ... or download via SCP
```

---

## Scale Beyond Free Tier

When you outgrow free tier:

1. **Add more Compute instances** (pay-as-you-go)
2. **Scale Autonomous Database** (pay for storage/compute)
3. **Add Load Balancer**
4. **Add CDN** for frontend

Total estimated cost: $20-50/month for production-grade deployment.

---

## Estimated Monthly Costs (Always-Free)

- Compute: **Free** (4 OCPU, 24GB RAM)
- Database: **Free** (20GB autonomous)
- Storage: **Free** (20GB object storage)
- Networking: **Free** (10GB/month outbound)

**Total: $0/month** ✅

---

## Troubleshooting

### Backend won't connect to database

```bash
# Check database status
docker logs unigpu-backend | grep "database"

# Verify connection string
echo $DATABASE_URL

# Test connection manually
python -c "import asyncpg; asyncio.run(asyncpg.connect('...'))"
```

### Redis connection failed

```bash
# Check Redis service
sudo systemctl status redis-server

# Restart Redis
sudo systemctl restart redis-server

# Test Redis
redis-cli ping
```

### SSL certificate expired

```bash
# Renew certificate
sudo certbot renew

# Auto-renewal should handle this, but manual refresh:
sudo systemctl restart nginx
```

### Running out of free tier quota

- Check Oracle Console → Quotas
- Monitor compute usage
- Archive old job files to Object Storage

---

## Next Steps

1. **Fix security vulnerabilities** (see SECURITY_AUDIT.md)
2. **Set up monitoring** (Oracle Cloud Monitoring)
3. **Configure backups** (Oracle Database Backups)
4. **Add domain** (Freenom or your registrar)
5. **Get SSL certificate** (Let's Encrypt via Certbot)
6. **Deploy agents** on user machines (distribute .exe from `agent/build/`)


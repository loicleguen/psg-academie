# Deployment Checklist

Use this checklist when deploying Veo Module V1 to production.

## Pre-Deployment

### Environment Setup
- [ ] Create production `.env` file
- [ ] Set strong `POSTGRES_ROOT_PASSWORD`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure production `DATABASE_URL`
- [ ] Set production `CORS_ORIGINS` (frontend URLs)
- [ ] Review `API_HOST` and `API_PORT`
- [ ] Add `JWT_SECRET` for V2 (optional)

### Security
- [ ] Change default database passwords
- [ ] Restrict database access to API only
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Review CORS settings
- [ ] Set up backup strategy
- [ ] Configure logging

### Database
- [ ] Verify POSTGRES version (16+)
- [ ] Test database connection
- [ ] Run migrations: `alembic upgrade head`
- [ ] Seed metrics: `python -m app.seed`
- [ ] Create database backups
- [ ] Test backup restoration

### Testing
- [ ] Run all tests: `pytest`
- [ ] Test API health endpoint
- [ ] Test each CRUD endpoint
- [ ] Test metrics bulk operations
- [ ] Test analytics endpoints
- [ ] Verify frontend loads correctly
- [ ] Test complete workflow (season → team → players → match → stats)

## Deployment Steps

### Backend (Docker)

```bash
# 1. Build production image
docker-compose -f docker-compose.yml build --no-cache

# 2. Start services
docker-compose up -d

# 3. Check logs
docker-compose logs -f api

# 4. Verify health
curl http://localhost:8000/health

# 5. Check API docs
# Visit: http://your-domain:8000/docs
```

### Frontend (Production Build)

```bash
cd frontend

# 1. Update API base URL in .env or vite.config.js
# VITE_API_BASE_URL=https://api.your-domain.com

# 2. Build for production
npm run build

# 3. Preview build locally
npm run preview

# 4. Deploy dist/ folder to web server
# - Option A: Copy to nginx/apache
# - Option B: Use Vercel/Netlify
# - Option C: Serve with Node.js
```

### Nginx Configuration (Optional)

```nginx
# /etc/nginx/sites-available/veo

# API reverse proxy
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Frontend static files
server {
    listen 80;
    server_name veo.your-domain.com;

    root /var/www/veo/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Post-Deployment

### Verification
- [ ] API responds at production URL
- [ ] Frontend loads correctly
- [ ] Login to POSTGRES and verify tables exist
- [ ] Test creating a season
- [ ] Test creating a team
- [ ] Test creating a player
- [ ] Test creating a match
- [ ] Test adding metrics
- [ ] Test analytics endpoints
- [ ] Check database contains seeded metrics

### Monitoring Setup
- [ ] Set up application logging
- [ ] Configure error tracking (e.g., Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure database monitoring
- [ ] Set up performance monitoring
- [ ] Configure backup alerts

### Documentation
- [ ] Update README with production URLs
- [ ] Document deployment process
- [ ] Create admin credentials doc
- [ ] Document backup/restore procedures
- [ ] Create troubleshooting guide
- [ ] Document rollback procedure

### User Training
- [ ] Create user accounts (if auth enabled)
- [ ] Train on dashboard usage
- [ ] Train on data entry workflow
- [ ] Provide quick reference card
- [ ] Schedule support availability

## Production Environment Variables

```bash
# Database
DATABASE_URL=postgresql+psycopg://veo_user:veo_password@localhost:5432/veo_db
POSTGRES_ROOT_PASSWORD=STRONG_ROOT_PASSWORD
POSTGRES_DATABASE=veo_db
POSTGRES_USER=veo_user
POSTGRES_PASSWORD=STRONG_PASSWORD

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False

# CORS
CORS_ORIGINS=https://veo.your-domain.com,https://www.your-domain.com

# Future: Auth (V2)
# JWT_SECRET=your-random-256-bit-secret
# JWT_ALGORITHM=HS256
# JWT_EXPIRATION=86400
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop containers
docker-compose down

# 2. Restore database from backup
docker compose exec -T postgres psql -U veo_user -d veo_db < backup.sql

# 3. Revert to previous version
git checkout <previous-tag>

# 4. Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# 5. Verify rollback
curl http://localhost:8000/health
```

## Backup Strategy

### Daily Backups

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/veo"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T postgres pg_dump \
  -U veo_user \
  -d veo_db \
  -Fc \
  > $BACKUP_DIR/veo_db_$DATE.dump

# Compress
gzip $BACKUP_DIR/veo_db_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: veo_db_$DATE.sql.gz"
```

Add to cron:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/veo_backup.log 2>&1
```

## Monitoring Commands

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f postgres

# Check API health
curl http://localhost:8000/health

# Check database connection
docker-compose exec api python -c "from app.db.session import engine; engine.connect()"

# Check disk usage
docker system df

# Database size
docker compose exec -T postgres psql -U veo_user -d veo_db -c \
"SELECT pg_size_pretty(pg_database_size('veo_db')) AS \"Size (MB)\";"
```

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_matches_team_season ON matches(team_id, season_id);
CREATE INDEX idx_matches_date ON matches(date);
CREATE INDEX idx_participations_player ON match_player_participations(player_id);
CREATE INDEX idx_team_metrics_match ON team_match_metric_values(match_id);
CREATE INDEX idx_player_metrics_match_player ON player_match_metric_values(match_id, player_id);
```

### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          memory: 512M

  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          memory: 256M
```

## Troubleshooting

### API won't start
```bash
# Check logs
docker-compose logs api

# Check database connection
docker-compose exec api python -c "from app.db.session import engine; print(engine.url)"

# Verify environment variables
docker-compose exec api env | grep DATABASE
```

### Database connection errors
```bash
# Check Postgres container status
docker compose ps postgres

# Check Postgres logs
docker compose logs postgres

# Test connection (simple query)
docker compose exec -T postgres psql -U veo_user -d veo_db -c "SELECT 1;"
```

### Migration errors
```bash
# Check current version
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Force to specific version
docker-compose exec api alembic stamp head
```

## Support Contacts

- Technical Lead: [Name] ([email])
- Database Admin: [Name] ([email])
- DevOps: [Name] ([email])
- Product Owner: [Name] ([email])

## Incident Response

1. **Assess severity** (Critical/High/Medium/Low)
2. **Check monitoring** (logs, metrics, alerts)
3. **Identify root cause**
4. **Apply fix** or **rollback**
5. **Verify resolution**
6. **Document incident**
7. **Post-mortem** (if critical)

## Success Criteria

- [ ] API responds within 500ms
- [ ] Database queries < 100ms
- [ ] Frontend loads < 2 seconds
- [ ] Zero downtime during deployment
- [ ] All tests passing
- [ ] Backups running successfully
- [ ] Monitoring alerts configured
- [ ] Documentation complete
- [ ] Users trained
- [ ] Support team ready

## Sign-Off

- [ ] Development Team: _____________
- [ ] QA Team: _____________
- [ ] DevOps Team: _____________
- [ ] Product Owner: _____________
- [ ] Date: _____________

---

**Deployment Status**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

**Production URL**: _________________________

**Deployment Date**: _________________________

**Deployed By**: _________________________

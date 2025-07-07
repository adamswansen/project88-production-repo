# Project88 Dashboard

Comprehensive analytics dashboard for the Project88 Race Timing Platform, providing real-time insights into events, participants, providers, and timing partners.

## 🎯 **Features**

### **Platform Overview**
- **Total Events**: 13,819+ across all providers
- **Total Participants**: 2,420,628+ registered users
- **Total Results**: 7,644,980+ timing records
- **Timing Partners**: 13 active companies

### **Provider Analytics**
- **RunSignUp**: 937 events, 38,362 participants
- **ChronoTrack**: 12,882 events, 2,382,266 participants, 7,644,980 results
- **Ready Providers**: Race Roster, Copernico, Haku (awaiting data)

### **Timing Partner Filtering**
- Filter all metrics by specific timing partner
- Individual company analytics
- Multi-tenant data isolation

### **Real-time Metrics**
- Live system health monitoring
- Recent activity feed
- Database and cache status
- API response monitoring

## 🏗️ **Architecture**

### **Backend (Flask)**
- **API Endpoints**: Comprehensive REST API for all metrics
- **Database**: PostgreSQL with 10.8M+ records
- **Caching**: Redis for performance optimization
- **Multi-tenant**: Timing partner isolation and filtering

### **Frontend (React)**
- **Modern UI**: Responsive dashboard with glassmorphism design
- **Real-time Updates**: Auto-refresh every 60 seconds
- **Interactive Filtering**: Dynamic timing partner selection
- **Chart Visualization**: Provider and trend analytics

## 🚀 **Quick Start**

### **Prerequisites**
```bash
# Python 3.9+
python --version

# PostgreSQL running with project88_myappdb
psql -h localhost -U postgres -d project88_myappdb -c "SELECT COUNT(*) FROM timing_partners;"

# Redis server running
redis-cli ping
```

### **Installation**
```bash
# Clone repository
cd project88-production-repo/apps/dashboard

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Start dashboard
cd ..
python start_dashboard.py
```

### **Production Deployment**
```bash
# Using Gunicorn
cd backend
gunicorn -w 4 -b 0.0.0.0:5004 app:app

# Using systemd service
sudo cp dashboard.service /etc/systemd/system/
sudo systemctl enable dashboard.service
sudo systemctl start dashboard.service
```

## 📊 **API Endpoints**

### **Core Metrics**
- `GET /api/overview?timing_partner_id=all` - Platform overview statistics
- `GET /api/providers?timing_partner_id=all` - Provider breakdown and status
- `GET /api/timing-partners` - All timing partners with statistics
- `GET /api/analytics?timing_partner_id=all` - Trends and analytics

### **Real-time**
- `GET /api/real-time` - Live system metrics and activity feed
- `GET /api/health` - System health check

### **Filtering**
All endpoints support `timing_partner_id` parameter:
- `timing_partner_id=all` - All timing partners (default)
- `timing_partner_id=1` - Specific timing partner

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project88_myappdb
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application
PORT=5004
DEBUG=False
CACHE_TTL=300
```

### **Database Tables Used**
- `timing_partners` - Timing company information
- `runsignup_events`, `runsignup_participants` - RunSignUp data
- `ct_events`, `ct_participants`, `ct_results` - ChronoTrack data
- `raceroster_events`, `raceroster_participants` - Race Roster data
- `copernico_events`, `copernico_participants`, `copernico_results` - Copernico data
- `haku_events`, `haku_participants` - Haku data
- `unified_participants`, `unified_events`, `unified_results` - Cross-provider views
- `sync_history` - Data synchronization logs

## 🌐 **Production Setup**

### **Domain Configuration**
Add to your Apache configuration:
```apache
<VirtualHost *:443>
    ServerName dashboard.project88hub.com
    ProxyPass / http://localhost:5004/
    ProxyPassReverse / http://localhost:5004/
    
    SSLEngine on
    SSLCertificateFile /path/to/your/cert.pem
    SSLCertificateKeyFile /path/to/your/key.pem
</VirtualHost>
```

### **Systemd Service**
```ini
[Unit]
Description=Project88 Dashboard
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=appuser
WorkingDirectory=/home/appuser/projects/project88-production-repo/apps/dashboard
ExecStart=/usr/bin/python3 start_dashboard.py
Restart=always
RestartSec=10
Environment=FLASK_ENV=production

[Install]
WantedBy=multi-user.target
```

## 📈 **Performance**

### **Caching Strategy**
- **Overview metrics**: 5-minute cache
- **Provider stats**: 5-minute cache
- **Real-time metrics**: 30-second cache
- **Redis fallback**: Graceful degradation if Redis unavailable

### **Database Optimization**
- **Connection pooling**: Single connection with retry logic
- **Query optimization**: Efficient joins and unified views
- **Indexes**: Proper indexing on timing_partner_id and timestamps

## 🔍 **Monitoring**

### **Health Checks**
- `GET /api/health` - System health endpoint
- Database connectivity test
- Redis connectivity test
- Service uptime monitoring

### **Logging**
- Application logs: `dashboard.log`
- Error tracking with timestamps
- Database query logging
- Performance metrics

## 🛠️ **Development**

### **Local Development**
```bash
# Start in development mode
FLASK_ENV=development python start_dashboard.py

# Enable debug mode
DEBUG=True python start_dashboard.py
```

### **Adding New Metrics**
1. Add database query to appropriate API endpoint
2. Update frontend component to display new data
3. Add to React state management
4. Update caching strategy if needed

## 🎯 **Integration with Project88**

### **Existing Services**
- **Race Display** (port 5001) - Main race timing display
- **Timing Collector** (port 61611) - ChronoTrack data collection
- **Authentication** (port 5002) - User authentication
- **User Management** (port 5003) - Subscription management
- **Database API** (port 3000) - PostgreSQL API
- **AI Platform** (port 8501) - Natural language queries

### **Dashboard Service** (port 5004)
- **New Service**: `dashboard.project88hub.com`
- **Integration**: Uses same database and Redis
- **Authentication**: Can be integrated with existing auth system
- **Multi-tenant**: Respects timing partner isolation

## 🚨 **Production Notes**

⚠️ **LIVE SYSTEM**: This dashboard connects to the live production database serving 13 timing partners.

⚠️ **DATA INTEGRITY**: All queries are read-only to ensure data safety.

⚠️ **PERFORMANCE**: Caching is essential for production performance with 10.8M+ records.

---

**Status**: Ready for Production Deployment  
**Port**: 5004  
**Domain**: dashboard.project88hub.com  
**Dependencies**: PostgreSQL, Redis, Python 3.9+ 
# RunSignUp Server Deployment Package

## Quick Start

1. **Upload this entire directory to your server**:
   ```bash
   scp -r runsignup_server_package/ user@your-server:/path/to/project88/provider-integrations/
   ```

2. **SSH to your server and navigate to the directory**:
   ```bash
   ssh user@your-server
   cd /path/to/project88/provider-integrations
   ```

3. **Run the deployment script**:
   ```bash
   chmod +x deploy_runsignup_production.sh
   ./deploy_runsignup_production.sh
   ```

## Files Included

- `runsignup_production_sync.py` - Main sync orchestrator
- `deploy_runsignup_production.sh` - Automated deployment script
- `providers/` - RunSignUp API adapter modules
- `requirements.txt` - Python dependencies
- `RUNSIGNUP_PRODUCTION_IMPLEMENTATION.md` - Complete implementation docs
- `SERVER_DEPLOYMENT_GUIDE.md` - Detailed server deployment guide

## What This Package Does

✅ **Syncs RunSignUp data** from all your timing partner accounts  
✅ **Handles authentication** and API communication  
✅ **Stores data** in your Project88Hub database  
✅ **Provides logging** and monitoring  
✅ **Includes deployment automation**  

## Need Help?

See `SERVER_DEPLOYMENT_GUIDE.md` for complete deployment instructions and troubleshooting.

---
**Package Created**: $(date)  
**Status**: Ready for Server Deployment

#!/bin/bash
# Create Server Deployment Package
# This script creates a clean package with only the files needed for server deployment

echo "🎁 Creating RunSignUp Server Deployment Package"
echo "================================================"

# Create package directory
PACKAGE_DIR="runsignup_server_package"
rm -rf $PACKAGE_DIR
mkdir -p $PACKAGE_DIR

echo "📦 Packaging essential files..."

# Copy core sync files
cp runsignup_production_sync.py $PACKAGE_DIR/
cp deploy_runsignup_production.sh $PACKAGE_DIR/
cp requirements.txt $PACKAGE_DIR/

# Copy provider adapter files
mkdir -p $PACKAGE_DIR/providers
cp providers/__init__.py $PACKAGE_DIR/providers/
cp providers/base_adapter.py $PACKAGE_DIR/providers/
cp providers/runsignup_adapter.py $PACKAGE_DIR/providers/

# Copy documentation
cp RUNSIGNUP_PRODUCTION_IMPLEMENTATION.md $PACKAGE_DIR/
cp SERVER_DEPLOYMENT_GUIDE.md $PACKAGE_DIR/

# Create README for the package
cat > $PACKAGE_DIR/README_DEPLOYMENT.md << 'EOF'
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
EOF

# Make deployment script executable
chmod +x $PACKAGE_DIR/deploy_runsignup_production.sh

# Create archive
tar -czf runsignup_server_package.tar.gz $PACKAGE_DIR

echo "✅ Package created successfully!"
echo ""
echo "📁 Files packaged:"
echo "   • runsignup_production_sync.py"
echo "   • deploy_runsignup_production.sh"
echo "   • providers/ (adapter modules)"
echo "   • requirements.txt"
echo "   • Documentation files"
echo ""
echo "📦 Package locations:"
echo "   • Directory: ./$PACKAGE_DIR/"
echo "   • Archive:   ./runsignup_server_package.tar.gz"
echo ""
echo "🚀 Next Steps:"
echo "   1. Upload package to your server"
echo "   2. Extract and run deployment script"
echo "   3. See SERVER_DEPLOYMENT_GUIDE.md for details"
echo ""
echo "📤 Upload command example:"
echo "   scp runsignup_server_package.tar.gz user@your-server:~/"
echo "   ssh user@your-server"
echo "   tar -xzf runsignup_server_package.tar.gz"
echo "   cd runsignup_server_package"
echo "   ./deploy_runsignup_production.sh" 
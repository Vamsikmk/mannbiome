# 🚀 MannBiome Deployment Guide

## Complete Deployment Script

Use `deploy-all.ps1` to deploy both backend and frontend with a single command.

---

## Prerequisites

Before running deployment:

1. **AWS CLI** configured with credentials
   ```powershell
   aws configure
   ```

2. **Docker Desktop** running (for backend)

3. **Node.js & npm** installed (for frontend)

4. **PowerShell Execution Policy** (run once if needed):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

---

## 🎯 Quick Start - Deploy Everything

```powershell
./deploy-all.ps1
```

This will:
1. ✅ Build & push Docker image to ECR
2. ✅ Deploy backend to App Runner
3. ✅ Build React frontend
4. ✅ Sync to S3
5. ✅ Invalidate CloudFront cache

---

## 📋 Deployment Options

### Deploy Only Backend (API)
```powershell
./deploy-all.ps1 -BackendOnly
```

### Deploy Only Frontend (React)
```powershell
./deploy-all.ps1 -FrontendOnly
```

### Skip CloudFront Cache Invalidation
```powershell
./deploy-all.ps1 -SkipCacheInvalidation
```

### Combine Options
```powershell
./deploy-all.ps1 -FrontendOnly -SkipCacheInvalidation
```

---

## 🔍 Manual Commands (if needed)

### Backend Deployment
```powershell
# 1. Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 088462465887.dkr.ecr.us-east-2.amazonaws.com

# 2. Build Docker image
docker build -t mannbiome-customer-portal-api .

# 3. Tag image
docker tag mannbiome-customer-portal-api:latest 088462465887.dkr.ecr.us-east-2.amazonaws.com/mannbiome-customer-portal-api:latest

# 4. Push to ECR
docker push 088462465887.dkr.ecr.us-east-2.amazonaws.com/mannbiome-customer-portal-api:latest

# 5. Check App Runner deployment
aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-2:088462465887:service/mannbiome-customer-portal --query 'Service.Status'
```

### Frontend Deployment
```powershell
# 1. Build React app
npm run build

# 2. Sync to S3
aws s3 sync build/ s3://mannbiome-customer-portal-frontend-088462465887 --delete

# 3. Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E47LTJIFSM54C --paths "/*"
```

---

## 🌐 Application URLs

- **Frontend (CloudFront):** https://dfjabnv013m4m.cloudfront.net
- **Backend (App Runner):** https://gnss5bq5km.us-east-2.awsapprunner.com

---

## 📊 Monitoring

### Check App Runner Status
```powershell
aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-2:088462465887:service/mannbiome-customer-portal
```

### View App Runner Logs
Go to: https://console.aws.amazon.com/apprunner/home?region=us-east-2#/services

### Check CloudFront Invalidation Status
```powershell
aws cloudfront list-invalidations --distribution-id E47LTJIFSM54C
```

---

## ⚠️ Troubleshooting

### Frontend shows old content
- Wait 1-3 minutes for CloudFront invalidation to complete
- Use Ctrl+Shift+R (hard refresh) in browser
- Clear browser cache

### Docker build fails
- Ensure Docker Desktop is running
- Check `dockerfile` for syntax errors
- Verify all required files exist

### ECR login fails
- Run `aws configure` to set credentials
- Verify IAM permissions for ECR

### App Runner deployment failed
- Check App Runner console for error logs
- Verify environment variables are set correctly
- Check if service has rolled back

### S3 sync fails
- Verify bucket name: `mannbiome-customer-portal-frontend-088462465887`
- Check IAM permissions for S3
- Ensure `build/` directory exists

---

## 🔄 Typical Deployment Workflow

### For Code Changes (Backend)
```powershell
./deploy-all.ps1 -BackendOnly
```

### For UI Changes (Frontend)
```powershell
./deploy-all.ps1 -FrontendOnly
```

### For Complete Updates
```powershell
./deploy-all.ps1
```

---

## ⏱️ Expected Deployment Times

- **Backend:** 3-5 minutes (Docker build + ECR push + App Runner deploy)
- **Frontend:** 2-3 minutes (React build + S3 sync + CloudFront invalidation)
- **Total:** 5-8 minutes for complete deployment

---

## 📝 Notes

1. App Runner automatically detects new ECR images and redeploys
2. CloudFront invalidation is required after S3 sync to serve updated files
3. The script includes automatic error checking and rollback information
4. All deployments are logged with colored output for easy tracking

---

## 🆘 Support

If deployment fails:
1. Check the error message in PowerShell
2. Review AWS console for detailed logs
3. Verify all environment variables in `.env` file
4. Ensure all AWS resources exist (ECR, App Runner, S3, CloudFront)

---

Last Updated: January 5, 2026

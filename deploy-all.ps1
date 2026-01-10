# ============================================
# MannBiome Customer Portal - Complete Deployment Script
# Deploys both Backend (App Runner) and Frontend (S3 + CloudFront)
# Account ID: 088462465887
# Region: us-east-2
# ============================================

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$SkipTests,
    [switch]$SkipCacheInvalidation
)

# Colors for output
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Configuration
$AWS_ACCOUNT_ID = "088462465887"
$AWS_REGION = "us-east-2"
$ECR_REPOSITORY = "mannbiome-customer-portal-api"
$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
$APPRUNNER_SERVICE = "mannbiome-customer-portal"
$S3_BUCKET = "mannbiome-customer-portal-frontend-$AWS_ACCOUNT_ID"
$CLOUDFRONT_DISTRIBUTION_ID = "E47LTJIFSM54C"
$CLOUDFRONT_URL = "https://dfjabnv013m4m.cloudfront.net"

Write-Info "=========================================="
Write-Info "MannBiome Complete Deployment Script"
Write-Info "=========================================="
Write-Info "Account: $AWS_ACCOUNT_ID"
Write-Info "Region: $AWS_REGION"
Write-Info ""

# Check if on main branch
Write-Info "Checking Git branch..."
try {
    $currentBranch = git rev-parse --abbrev-ref HEAD 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to get current Git branch. Are you in a Git repository?"
        exit 1
    }
    
    Write-Info "Current branch: $currentBranch"
    
    if ($currentBranch -ne "main") {
        Write-Error "=========================================="
        Write-Error "DEPLOYMENT BLOCKED"
        Write-Error "=========================================="
        Write-Error "You are on branch: $currentBranch"
        Write-Error "Deployments are only allowed from the 'main' branch."
        Write-Error ""
        Write-Info "To deploy, please:"
        Write-Info "  1. Switch to main: git checkout main"
        Write-Info "  2. Merge your changes: git merge $currentBranch"
        Write-Info "  3. Run deployment again"
        Write-Error ""
        exit 1
    }
    
    Write-Success "On main branch - proceeding with deployment"
} catch {
    Write-Error "Failed to verify Git branch"
    exit 1
}

# Check if AWS CLI is configured
Write-Info "Checking AWS credentials..."
try {
    $identity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    }
    Write-Success "AWS credentials verified"
} catch {
    Write-Error "Failed to verify AWS credentials"
    exit 1
}

# ============================================
# BACKEND DEPLOYMENT
# ============================================
if (-not $FrontendOnly) {
    Write-Info ""
    Write-Info "=========================================="
    Write-Info "BACKEND DEPLOYMENT (Docker + App Runner)"
    Write-Info "=========================================="
    
    # Step 1: ECR Login
    Write-Info "Step 1/5: Logging into ECR..."
    $loginCommand = "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    Invoke-Expression $loginCommand
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ECR login failed"
        exit 1
    }
    Write-Success "ECR login successful"
    
    # Step 2: Build Docker Image
    Write-Info "Step 2/5: Building Docker image..."
    docker build -t mannbiome-customer-portal-api .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
        exit 1
    }
    Write-Success "Docker image built successfully"
    
    # Step 3: Tag Docker Image
    Write-Info "Step 3/5: Tagging Docker image..."
    $tagTarget = "${ECR_URI}:latest"
    docker tag mannbiome-customer-portal-api:latest $tagTarget
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker tag failed"
        exit 1
    }
    Write-Success "Docker image tagged"
    
    # Step 4: Push to ECR
    Write-Info "Step 4/5: Pushing image to ECR..."
    docker push $tagTarget
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker push failed"
        exit 1
    }
    Write-Success "Docker image pushed to ECR"
    
    # Step 5: Check App Runner Deployment
    Write-Info "Step 5/5: Checking App Runner deployment status..."
    Write-Warning "Waiting for App Runner to detect and deploy new image..."
    Write-Info "Checking status in 30 seconds..."
    Start-Sleep -Seconds 30
    
    $serviceStatus = aws apprunner describe-service --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${APPRUNNER_SERVICE}" --query 'Service.Status' --output text 2>&1
    
    if ($serviceStatus -match "OPERATION_IN_PROGRESS") {
        Write-Warning "Deployment in progress..."
        Write-Info "Monitor deployment at: https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION#/services"
    } elseif ($serviceStatus -match "RUNNING") {
        Write-Success "App Runner service is RUNNING"
    } else {
        Write-Warning "App Runner status: $serviceStatus"
        Write-Info "Check the console for details"
    }
    
    $serviceUrl = aws apprunner describe-service --service-arn "arn:aws:apprunner:${AWS_REGION}:${AWS_ACCOUNT_ID}:service/${APPRUNNER_SERVICE}" --query 'Service.ServiceUrl' --output text 2>&1
    if ($serviceUrl) {
        Write-Success "Backend URL: https://$serviceUrl"
    }
    
    Write-Success ""
    Write-Success "BACKEND DEPLOYMENT COMPLETED"
}

# ============================================
# FRONTEND DEPLOYMENT
# ============================================
if (-not $BackendOnly) {
    Write-Info ""
    Write-Info "=========================================="
    Write-Info "FRONTEND DEPLOYMENT (React + S3 + CloudFront)"
    Write-Info "=========================================="
    
    # Step 1: Install dependencies (if needed)
    if (-not (Test-Path "node_modules")) {
        Write-Info "Step 1/4: Installing npm dependencies..."
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install failed"
            exit 1
        }
        Write-Success "Dependencies installed"
    } else {
        Write-Success "Step 1/4: Dependencies already installed"
    }
    
    # Step 2: Build React app
    Write-Info "Step 2/4: Building React application..."
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "React build failed"
        exit 1
    }
    Write-Success "React build completed"
    
    # Step 3: Sync to S3
    Write-Info "Step 3/4: Syncing build to S3..."
    aws s3 sync build/ "s3://$S3_BUCKET" --delete
    if ($LASTEXITCODE -ne 0) {
        Write-Error "S3 sync failed"
        exit 1
    }
    Write-Success "Files synced to S3"
    
    # Step 4: Invalidate CloudFront cache
    if (-not $SkipCacheInvalidation) {
        Write-Info "Step 4/4: Invalidating CloudFront cache..."
        $invalidationId = aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*" --query 'Invalidation.Id' --output text
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "CloudFront invalidation failed (but files are uploaded)"
        } else {
            Write-Success "CloudFront cache invalidation initiated (ID: $invalidationId)"
            Write-Info "Cache invalidation may take 1-3 minutes to complete"
        }
    } else {
        Write-Warning "Skipping CloudFront cache invalidation"
    }
    
    Write-Success ""
    Write-Success "FRONTEND DEPLOYMENT COMPLETED"
    Write-Success "Frontend URL: $CLOUDFRONT_URL"
}

# ============================================
# DEPLOYMENT SUMMARY
# ============================================
Write-Info ""
Write-Info "=========================================="
Write-Info "DEPLOYMENT SUMMARY"
Write-Info "=========================================="

if (-not $FrontendOnly) {
    Write-Info "Backend (App Runner):"
    Write-Info "  - ECR Repository: $ECR_URI"
    Write-Info "  - Service: $APPRUNNER_SERVICE"
    Write-Info "  - Console: https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION#/services"
}

if (-not $BackendOnly) {
    Write-Info "Frontend (S3 + CloudFront):"
    Write-Info "  - S3 Bucket: $S3_BUCKET"
    Write-Info "  - CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
    Write-Info "  - CloudFront URL: $CLOUDFRONT_URL"
}

Write-Info ""
Write-Success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
Write-Info ""
Write-Info "Next Steps:"
Write-Info "  1. Wait 1-3 minutes for CloudFront cache to clear (if frontend deployed)"
Write-Info "  2. Test your application at: $CLOUDFRONT_URL"
Write-Info "  3. Check App Runner logs if backend issues occur"
Write-Info ""
Write-Warning "If you see old content, wait for CloudFront invalidation to complete"
Write-Info "    or hard refresh your browser with Ctrl+Shift+R"
Write-Info ""

# GitHub CI/CD Setup Instructions

## Step 1: Create GitHub Repository

```bash
# Initialize git (if not already)
cd /Users/sanojma/Desktop/GenappAWS
git init

# Add remote origin
git remote add origin https://github.com/sanojvelloth8/GenappAWS.git

# Create .gitignore
echo ".terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl" > .gitignore
```

## Step 2: Deploy OIDC Provider First (Locally)

```bash
cd terraform
terraform init
terraform apply -auto-approve
```

This creates:
- OIDC Identity Provider
- IAM Role for GitHub Actions

Copy the output: `github_actions_role_arn`

## Step 3: Add Secret to GitHub

1. Go to: https://github.com/sanojvelloth8/GenappAWS/settings/secrets/actions
2. Click "New repository secret"
3. Name: `AWS_ROLE_ARN`
4. Value: (paste the role ARN from Step 2)

## Step 4: Push to GitHub

```bash
git add .
git commit -m "Initial commit with CI/CD"
git branch -M main
git push -u origin main
```

## Step 5: Watch the Magic! 🚀

1. Go to: https://github.com/sanojvelloth8/GenappAWS/actions
2. You'll see the "Deploy GenApp" workflow running
3. After ~15-20 minutes, deployment will be complete!

## Security Notes

- OIDC role is restricted to `sanojvelloth8/GenappAWS:main` only
- No AWS credentials stored in GitHub
- Token valid only for the duration of the workflow run

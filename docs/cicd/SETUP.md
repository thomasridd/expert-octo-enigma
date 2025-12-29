# CI/CD Pipeline Setup Guide

This guide walks you through setting up a complete CI/CD pipeline for the Alexa Leaving Timer Skill using GitHub Actions and AWS.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Step 1: Create AWS IAM User](#step-1-create-aws-iam-user)
- [Step 2: Configure GitHub Secrets](#step-2-configure-github-secrets)
- [Step 3: Configure GitHub Environments](#step-3-configure-github-environments)
- [Step 4: Test the Pipeline](#step-4-test-the-pipeline)
- [Workflows Overview](#workflows-overview)
- [Troubleshooting](#troubleshooting)

## Overview

The CI/CD pipeline consists of two workflows:

1. **Test Workflow** (`.github/workflows/test.yml`): Runs on every pull request and push to main
   - Runs unit tests with pytest
   - Validates SAM template
   - Validates Alexa skill configuration
   - Runs linting with flake8

2. **Deploy Workflow** (`.github/workflows/deploy.yml`): Runs on push to main or manual trigger
   - Deploys AWS infrastructure using SAM
   - Optionally deploys Alexa skill configuration
   - Supports multiple environments (dev, staging, prod)

## Prerequisites

- AWS Account with administrative access
- GitHub repository
- Basic knowledge of AWS IAM
- AWS CLI installed locally (for initial setup)

## Step 1: Create AWS IAM User

### 1.1 Log into AWS Console

1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **IAM** service
3. Click **Users** in the left sidebar

### 1.2 Create New User

1. Click **Create user** button
2. Enter username: `github-actions-leaving-timer`
3. Click **Next**

### 1.3 Attach Permissions

**Option A: Using the Provided Policy (Recommended)**

1. Select **Attach policies directly**
2. Click **Create policy**
3. Choose **JSON** tab
4. Copy the contents of `docs/cicd/iam-policy.json` and paste it
5. Click **Next: Tags** (optional)
6. Click **Next: Review**
7. Name the policy: `LeavingTimerSkillDeploymentPolicy`
8. Add description: "Policy for GitHub Actions to deploy Leaving Timer Skill"
9. Click **Create policy**
10. Go back to the user creation page and refresh the policies
11. Search for `LeavingTimerSkillDeploymentPolicy` and select it
12. Click **Next**

**Option B: Using AWS Managed Policies (Quick but less secure)**

1. Select **Attach policies directly**
2. Search and select these policies:
   - `AWSCloudFormationFullAccess`
   - `AWSLambda_FullAccess`
   - `IAMFullAccess` (or create a limited IAM policy)
   - `AmazonDynamoDBFullAccess`
   - `AmazonS3FullAccess`
   - `CloudWatchLogsFullAccess`
3. Click **Next**

> **Warning**: Option B grants broader permissions than necessary. Use Option A for production.

### 1.4 Review and Create

1. Review the user configuration
2. Click **Create user**

### 1.5 Create Access Keys

1. Click on the newly created user: `github-actions-leaving-timer`
2. Go to **Security credentials** tab
3. Scroll down to **Access keys**
4. Click **Create access key**
5. Select use case: **Third-party service**
6. Check the confirmation box
7. Click **Next**
8. Add description: "GitHub Actions deployment"
9. Click **Create access key**
10. **IMPORTANT**: Copy both:
    - Access key ID
    - Secret access key
11. Click **Done**

> **Security Note**: Store these credentials securely. You won't be able to see the secret access key again.

## Step 2: Configure GitHub Secrets

### 2.1 Navigate to Repository Settings

1. Go to your GitHub repository
2. Click **Settings** tab
3. In the left sidebar, expand **Secrets and variables**
4. Click **Actions**

### 2.2 Add Repository Secrets

Click **New repository secret** for each of the following:

#### Required AWS Secrets

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Your IAM access key ID | From Step 1.5 |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret access key | From Step 1.5 |

#### Required Alexa Skill Secrets

| Secret Name | Value | How to Get It |
|------------|-------|---------------|
| `ALEXA_SKILL_ID` | `amzn1.ask.skill.xxx` | From Alexa Developer Console → Your Skill → View Skill ID |

#### Optional Alexa Deployment Secrets (for skill auto-deployment)

| Secret Name | Value | How to Get It |
|------------|-------|---------------|
| `ASK_ACCESS_TOKEN` | LWA access token | See [ASK CLI Authentication](#ask-cli-authentication) |
| `ASK_REFRESH_TOKEN` | LWA refresh token | See [ASK CLI Authentication](#ask-cli-authentication) |
| `ASK_VENDOR_ID` | Your vendor ID | From Alexa Developer Console → Settings |

#### Optional Testing Secrets

| Secret Name | Value | Description |
|------------|-------|-------------|
| `CODECOV_TOKEN` | Codecov token | Optional: For code coverage reporting |

### 2.3 ASK CLI Authentication

To get ASK tokens for automated skill deployment:

```bash
# Install ASK CLI locally
npm install -g ask-cli

# Initialize ASK CLI
ask configure

# Follow the browser authentication flow

# Extract tokens from the config file
cat ~/.ask/cli_config
```

The tokens will be in the JSON output under `profiles.default.token`:
- `access_token` → Use for `ASK_ACCESS_TOKEN`
- `refresh_token` → Use for `ASK_REFRESH_TOKEN`

The vendor ID will be under `profiles.default.vendor_id` → Use for `ASK_VENDOR_ID`

## Step 3: Configure GitHub Environments

### 3.1 Create Environments

1. In your GitHub repository, go to **Settings** → **Environments**
2. Click **New environment**
3. Create three environments:
   - `dev`
   - `staging`
   - `prod`

### 3.2 Configure Protection Rules (Optional but Recommended)

For each environment, especially `prod`:

1. Click on the environment name
2. Check **Required reviewers**
3. Add reviewers who must approve deployments
4. Optionally set **Wait timer** (e.g., 5 minutes)
5. Click **Save protection rules**

### 3.3 Environment-Specific Secrets (Optional)

If you need different AWS accounts or skill IDs per environment:

1. Click on the environment name
2. Click **Add secret**
3. Add environment-specific secrets with the same names as repository secrets

Environment secrets override repository secrets for that environment.

## Step 4: Test the Pipeline

### 4.1 Test the Test Workflow

1. Create a new branch:
   ```bash
   git checkout -b test-ci-pipeline
   ```

2. Make a small change to trigger the workflow:
   ```bash
   echo "# Testing CI" >> lambda/tests/__init__.py
   git add .
   git commit -m "Test CI pipeline"
   git push origin test-ci-pipeline
   ```

3. Create a pull request on GitHub

4. Watch the **Checks** tab on your PR to see the test workflow run

5. Verify:
   - [ ] Python tests pass
   - [ ] SAM template validates
   - [ ] Skill package validates

### 4.2 Test the Deploy Workflow

**Option A: Automatic Deploy (on merge to main)**

1. Merge your test PR to main
2. Go to **Actions** tab in GitHub
3. Watch the **Deploy** workflow run
4. Check the deployment summary in the workflow run

**Option B: Manual Deploy**

1. Go to **Actions** tab in GitHub
2. Click **Deploy** workflow
3. Click **Run workflow** button
4. Select environment (dev, staging, or prod)
5. Click **Run workflow**
6. Monitor the deployment progress

### 4.3 Verify Deployment

After successful deployment:

1. Go to AWS Console → CloudFormation
2. Verify stack exists: `leaving-timer-skill-dev` (or your environment)
3. Check **Outputs** tab for Lambda ARN
4. Go to Lambda console and verify function exists
5. Go to DynamoDB console and verify table exists
6. Test the Alexa skill in the developer console

## Workflows Overview

### Test Workflow

**Triggers:**
- Pull requests to main
- Pushes to main
- Changes to `lambda/**` or workflow file

**Jobs:**
1. **test**: Runs on Python 3.11 and 3.12
   - Installs dependencies
   - Runs pytest with coverage
   - Uploads coverage to Codecov
   - Runs flake8 linting

2. **validate-sam-template**:
   - Validates CloudFormation template syntax

3. **validate-skill-package**:
   - Validates JSON syntax for skill configuration

### Deploy Workflow

**Triggers:**
- Push to main branch
- Manual trigger (workflow_dispatch)

**Jobs:**
1. **deploy-infrastructure**:
   - Builds SAM application
   - Deploys to AWS using CloudFormation
   - Runs smoke tests
   - Generates deployment summary

2. **deploy-skill** (conditional):
   - Only runs for prod environment
   - Deploys Alexa skill configuration using ASK CLI
   - Requires ASK tokens to be configured

**Environment Variables:**
- `AWS_REGION`: `eu-west-2` (configurable)
- `PYTHON_VERSION`: `3.11`

## Troubleshooting

### Common Issues

#### 1. "Access Denied" Errors

**Symptoms**: Workflow fails with IAM permission errors

**Solutions**:
- Verify IAM policy is attached to user
- Check the policy includes all required permissions
- Ensure access keys are correctly configured in GitHub secrets
- Try running `aws sts get-caller-identity` locally with the credentials

#### 2. "Stack already exists" Error

**Symptoms**: CloudFormation fails because stack already exists

**Solutions**:
```bash
# Delete the existing stack
aws cloudformation delete-stack --stack-name leaving-timer-skill-dev --region eu-west-2

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name leaving-timer-skill-dev --region eu-west-2
```

#### 3. SAM Build Fails

**Symptoms**: Build step fails in deploy workflow

**Solutions**:
- Check `requirements.txt` is valid
- Verify Python version compatibility
- Check CloudWatch logs for specific errors
- Try running `sam build` locally

#### 4. ASK CLI Authentication Fails

**Symptoms**: Skill deployment fails with authentication errors

**Solutions**:
- Regenerate ASK tokens using `ask configure`
- Verify tokens are not expired (access tokens expire in 1 hour)
- Use refresh tokens properly
- Consider skipping automated skill deployment and deploying manually

#### 5. Lambda Permission Errors

**Symptoms**: Alexa can't invoke Lambda function

**Solutions**:
- Verify Alexa Skills Kit trigger is configured
- Check the skill ID in SAM parameters matches your actual skill ID
- Manually add Lambda permission in AWS Console:
  ```bash
  aws lambda add-permission \
    --function-name leaving-timer-skill-dev-LeavingTimerFunction-XXX \
    --statement-id alexa-skill \
    --action lambda:InvokeFunction \
    --principal alexa-appkit.amazon.com \
    --event-source-token your-skill-id
  ```

### Debugging Tips

1. **Check Workflow Logs**:
   - Go to Actions tab → Click on failed workflow → Expand failed step
   - Look for specific error messages

2. **Check CloudFormation Events**:
   - AWS Console → CloudFormation → Select stack → Events tab
   - Look for failed resources

3. **Check Lambda Logs**:
   - AWS Console → CloudWatch → Log groups → `/aws/lambda/leaving-timer-skill-*`
   - Look for runtime errors

4. **Test Locally**:
   ```bash
   # Test SAM build
   cd infrastructure
   sam build
   sam validate --lint

   # Run tests
   cd ../lambda
   pytest tests/ -v
   ```

5. **Use AWS CloudShell**:
   - If local AWS CLI isn't working, use CloudShell in AWS Console
   - Test permissions and deployments directly

## Security Best Practices

1. **Rotate Access Keys Regularly**:
   - Every 90 days, create new access keys
   - Update GitHub secrets
   - Delete old access keys

2. **Use Least Privilege**:
   - Only grant permissions needed for deployment
   - Use the custom IAM policy, not managed policies in production

3. **Enable MFA for AWS Account**:
   - Protect your AWS root account with MFA
   - Consider MFA for IAM users with elevated permissions

4. **Monitor CloudTrail**:
   - Enable CloudTrail for audit logging
   - Monitor for suspicious API calls

5. **Use Environment Protection**:
   - Require approvals for production deployments
   - Set up deployment windows

6. **Secure GitHub Repository**:
   - Enable branch protection for main
   - Require PR reviews
   - Enable security scanning

## Advanced Configuration

### Multiple AWS Accounts

To deploy to different AWS accounts per environment:

1. Create IAM users in each AWS account
2. Add environment-specific secrets:
   - Environment: `prod` → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Environment: `staging` → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### Custom Domain Names

To use custom stack names per environment:

Edit `.github/workflows/deploy.yml`:

```yaml
--stack-name leaving-timer-skill-${{ github.event.inputs.environment || 'dev' }}
```

### Notifications

Add Slack notifications on deployment:

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)
- [ASK CLI Documentation](https://developer.amazon.com/docs/smapi/ask-cli-intro.html)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review workflow logs in GitHub Actions
3. Check CloudFormation events in AWS Console
4. Review CloudWatch logs for Lambda errors

For additional help, create an issue in the repository with:
- Workflow run URL
- Error messages
- Steps to reproduce

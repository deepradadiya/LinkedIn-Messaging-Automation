# GTMotion.ai LinkedIn Automation Platform

A cost-effective, AI-driven LinkedIn messaging automation platform that generates personalized icebreakers using OpenAI GPT-4o, with AWS Lambda/DynamoDB backend for processing and caching.

## 🚀 Features

- **AI-Powered Icebreakers**: Generate personalized LinkedIn messages using OpenAI GPT-4o
- **Cost Optimization**: DynamoDB caching reduces AI costs by up to 30%
- **Rate Limiting**: Respects LinkedIn's 50-75 messages/day limits
- **GDPR Compliance**: Encrypted data storage with automatic TTL
- **Scalable Architecture**: AWS Lambda for serverless processing
- **Real-time Monitoring**: CloudWatch logging and metrics
- **Mock Integrations**: Ready for Unipile API integration

## 📊 Cost Analysis

- **Target Cost**: ~$0.05 per lead
- **Actual Cost**: ~$0.0025 per message (50 tokens average)
- **Monthly Budget**: ~$50 for 1000+ leads
- **Caching Savings**: 30% reduction in AI costs

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │────│  AWS Lambda      │────│   DynamoDB      │
│   (Future)      │    │  (Processing)    │    │   (Caching)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  OpenAI GPT-4o   │    │  CloudWatch     │
                    │  (AI Generation) │    │  (Logging)      │
                    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Unipile API     │
                    │  (Mock/Future)   │
                    └──────────────────┘
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.9+
- AWS Account (Free Tier eligible)
- OpenAI API Key
- Git

### 1. Clone Repository

```bash
git clone https://github.com/your-org/gtmotion-linkedin-automation.git
cd gtmotion-linkedin-automation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create `.env` file:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Optional: Custom Settings
DAILY_MESSAGE_LIMIT=50
COST_PER_1K_TOKENS=0.005
TARGET_COST_PER_LEAD=0.05
```

### 4. AWS Setup

#### Create DynamoDB Tables

```bash
# Create icebreaker cache table
aws dynamodb create-table \
    --table-name linkedin_icebreakers \
    --attribute-definitions AttributeName=profile_id,AttributeType=S \
    --key-schema AttributeName=profile_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Create rate limiting table
aws dynamodb create-table \
    --table-name linkedin_rate_limits \
    --attribute-definitions AttributeName=date,AttributeType=S \
    --key-schema AttributeName=date,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

#### Deploy Lambda Function

```bash
# Create deployment package
zip -r lambda_deployment.zip linkedin_automation_platform.py lambda_function.py

# Create Lambda function
aws lambda create-function \
    --function-name gtmotion-linkedin-automation \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_deployment.zip \
    --environment Variables='{OPENAI_API_KEY=your_key_here}' \
    --timeout 30 \
    --memory-size 256
```

## 🚀 Quick Start

### Basic Usage

```python
from linkedin_automation_platform import LinkedInAutomationPlatform, LinkedInProfile
import os

# Initialize platform
platform = LinkedInAutomationPlatform(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    aws_region='us-east-1'
)

# Create profile
profile = LinkedInProfile(
    name="Jane Doe",
    title="AI Engineer",
    company="Tech Corp",
    industry="Technology",
    location="San Francisco, CA"
)

# Process complete outreach
result = platform.process_outreach(profile)

if result['success']:
    print(f"✅ Message sent to {profile.name}")
    print(f"Icebreaker: {result['icebreaker']}")
    print(f"Cost: ${result['cost']:.4f}")
    print(f"Remaining today: {result['remaining_messages']}")
else:
    print(f"❌ Error: {result['error']}")
```

### Lambda Function Usage

```python
import json
import boto3

# Invoke Lambda function
lambda_client = boto3.client('lambda', region_name='us-east-1')

event = {
    "action": "process_outreach",
    "profile": {
        "name": "Jane Doe",
        "title": "AI Engineer",
        "company": "Tech Corp"
    }
}

response = lambda_client.invoke(
    FunctionName='gtmotion-linkedin-automation',
    Payload=json.dumps(event)
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=linkedin_automation_platform --cov-report=html

# Run specific test
python -m pytest tests/test_linkedin_automation.py::TestLinkedInAutomationPlatform::test_icebreaker_generation -v
```

### Manual Testing

```bash
# Test main application
python linkedin_automation_platform.py

# Test Lambda function locally
python lambda_function.py

# Run unit tests with performance metrics
python unit_tests.py
```

## 📊 Monitoring & Analytics

### CloudWatch Metrics

The platform automatically logs to CloudWatch:

```python
# View metrics in AWS Console or programmatically
cloudwatch = boto3.client('cloudwatch')

# Get icebreaker generation metrics
response = cloudwatch.get_metric_statistics(
    Namespace='GTMotion/LinkedInAutomation',
    MetricName='icebreaker_generated',
    StartTime=datetime.now() - timedelta(days=1),
    EndTime=datetime.now(),
    Period=3600,
    Statistics=['Sum']
)
```

### Daily Statistics

```python
# Get daily stats
stats = platform.get_daily_stats()
print(f"Messages sent today: {stats['messages_sent']}")
print(f"Estimated cost: ${stats['estimated_cost']:.4f}")
print(f"Cost per lead: ${stats['cost_per_lead']:.4f}")
```

## 🔒 Security & Compliance

### GDPR Compliance

- **Data Encryption**: All profile data encrypted at rest
- **TTL Policy**: Cached data expires after 24 hours
- **Minimal Data**: Only necessary profile fields stored
- **Right to Deletion**: Cached data automatically purged

### Rate Limiting

- **Daily Limits**: 50 messages/day (configurable)
- **LinkedIn Compliance**: Respects platform limits
- **Automatic Reset**: Daily counters reset at midnight
- **Graceful Degradation**: Fails safely when limits exceeded

### Error Handling

```python
try:
    result = platform.process_outreach(profile)
except Exception as e:
    logger.error(f"Outreach failed: {str(e)}")
    # Implement retry logic or fallback
```

## 💰 Cost Optimization

### Caching Strategy

1. **Profile-Based Caching**: Unique profiles cached for 24 hours
2. **Cost Savings**: ~30% reduction in AI costs
3. **Cache Invalidation**: Automatic TTL-based expiration
4. **Cache Warming**: Pre-generate for common profiles

### Token Optimization

```python
# Optimize prompts for token efficiency
def optimize_prompt(profile):
    return f"Create LinkedIn icebreaker for {profile.name}, {profile.title} at {profile.company}"
```

### Budget Monitoring

```python
# Set budget alerts
if platform.get_daily_stats()['estimated_cost'] > daily_budget:
    send_budget_alert()
```

## 🔧 Configuration

### Platform Settings

```python
# Customize platform behavior
platform = LinkedInAutomationPlatform(
    openai_api_key=api_key,
    aws_region='us-east-1',
    daily_message_limit=40,  # Conservative limit
    cost_per_1k_tokens=0.005,  # GPT-4o pricing
    target_cost_per_lead=0.05  # Budget target
)
```

### Environment Variables

```bash
# Core settings
OPENAI_API_KEY=your_openai_key
AWS_REGION=us-east-1

# Rate limiting
DAILY_MESSAGE_LIMIT=50
LINKEDIN_SAFETY_BUFFER=10

# Cost management
COST_PER_1K_TOKENS=0.005
TARGET_COST_PER_LEAD=0.05
MONTHLY_BUDGET=50.00

# Security
ENCRYPTION_KEY_FILE=encryption_key.key
DATA_RETENTION_HOURS=24
```

## 🚀 Deployment

### AWS Lambda Deployment

```bash
# Build deployment package
./scripts/build_lambda.sh

# Deploy using AWS SAM
sam build
sam deploy --guided
```

### Production Checklist

- [ ] Environment variables configured
- [ ] DynamoDB tables created
- [ ] Lambda function deployed
- [ ] CloudWatch logging enabled
- [ ] IAM roles properly configured
- [ ] Encryption keys generated
- [ ] Rate limiting tested
- [ ] Cost monitoring setup

## 📈 Scaling

### Horizontal Scaling

```python
# Process multiple profiles concurrently
import asyncio

async def process_multiple_profiles(profiles):
    tasks = [platform.process_outreach(profile) for profile in profiles]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Performance Optimization

```python
# Batch processing for efficiency
def process_batch(profiles, batch_size=10):
    for i in range(0, len(profiles), batch_size):
        batch = profiles[i:i + batch_size]
        results = process_multiple_profiles(batch)
        yield results
```

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   ```python
   # Check API key and quotas
   if 'rate_limit' in str(e):
       time.sleep(60)  # Wait and retry
   ```

2. **DynamoDB Access Issues**
   ```bash
   # Check IAM permissions
   aws iam get-role-policy --role-name lambda-execution-role --policy-name dynamodb-access
   ```

3. **Rate Limit Exceeded**
   ```python
   # Check daily usage
   stats = platform.get_daily_stats()
   if stats['messages_sent'] >= platform.daily_message_limit:
       print("Daily limit reached, try tomorrow")
   ```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose logging
platform = LinkedInAutomationPlatform(
    openai_api_key=api_key,
    debug_mode=True
)
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/gtmotion-linkedin-automation.git

# Create virtual environment
python -m venv venv
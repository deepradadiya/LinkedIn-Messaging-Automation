import json
import os
import boto3
from datetime import datetime
from linkedin_automation_platform import LinkedInAutomationPlatform, LinkedInProfile

def lambda_handler(event, context):
    """
    AWS Lambda handler for LinkedIn automation platform
    
    Expected event structure:
    {
        "action": "process_outreach",
        "profile": {
            "name": "Jane Doe",
            "title": "AI Engineer", 
            "company": "Tech Corp",
            "industry": "Technology",
            "location": "San Francisco, CA"
        }
    }
    """
    
    try:
        # Initialize platform
        platform = LinkedInAutomationPlatform(
            openai_api_key=os.environ['OPENAI_API_KEY'],
            aws_region=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Parse event
        action = event.get('action', 'process_outreach')
        
        if action == 'process_outreach':
            # Extract profile data
            profile_data = event.get('profile', {})
            profile = LinkedInProfile(
                name=profile_data.get('name', ''),
                title=profile_data.get('title', ''),
                company=profile_data.get('company', ''),
                industry=profile_data.get('industry'),
                location=profile_data.get('location')
            )
            
            # Process outreach
            result = platform.process_outreach(profile)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
        elif action == 'get_stats':
            # Get daily statistics
            stats = platform.get_daily_stats()
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'data': stats,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
        elif action == 'generate_icebreaker':
            # Generate icebreaker only
            profile_data = event.get('profile', {})
            profile = LinkedInProfile(
                name=profile_data.get('name', ''),
                title=profile_data.get('title', ''),
                company=profile_data.get('company', ''),
                industry=profile_data.get('industry'),
                location=profile_data.get('location')
            )
            
            result = platform.generate_icebreaker(profile)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'data': {
                        'profile_id': result.profile_id,
                        'icebreaker': result.icebreaker,
                        'cost': result.cost,
                        'tokens_used': result.tokens_used,
                        'cached': result.cached
                    },
                    'timestamp': datetime.now().isoformat()
                })
            }
            
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Unknown action: {action}',
                    'timestamp': datetime.now().isoformat()
                })
            }
            
    except Exception as e:
        print(f"Lambda error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

# Test function for local development
def test_lambda_locally():
    """Test Lambda function locally"""
    test_event = {
        "action": "process_outreach",
        "profile": {
            "name": "Jane Doe",
            "title": "AI Engineer", 
            "company": "Tech Corp",
            "industry": "Technology",
            "location": "San Francisco, CA"
        }
    }
    
    # Set environment variables for testing
    os.environ['OPENAI_API_KEY'] = 'your-openai-api-key'
    os.environ['AWS_REGION'] = 'us-east-1'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_lambda_locally()
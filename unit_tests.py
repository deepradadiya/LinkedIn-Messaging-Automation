#!/usr/bin/env python3
"""
Unit tests for GTMotion.ai LinkedIn Automation Platform
"""

import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import boto3
from moto import mock_dynamodb

# Import our modules
from linkedin_automation_platform import LinkedInAutomationPlatform, LinkedInProfile, IcebreakerResult

class TestLinkedInAutomationPlatform(unittest.TestCase):
    """Test cases for LinkedIn Automation Platform"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_openai_key = "test-openai-key"
        self.test_profile = LinkedInProfile(
            name="Jane Doe",
            title="AI Engineer",
            company="Tech Corp",
            industry="Technology",
            location="San Francisco, CA"
        )
    
    @mock_dynamodb
    @patch('openai.OpenAI')
    @patch('boto3.client')
    def test_platform_initialization(self, mock_boto_client, mock_openai):
        """Test platform initialization"""
        # Mock CloudWatch client
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(
            openai_api_key=self.mock_openai_key,
            aws_region='us-east-1'
        )
        
        self.assertIsNotNone(platform.openai_client)
        self.assertEqual(platform.daily_message_limit, 50)
        self.assertEqual(platform.cost_per_1k_tokens, 0.005)
        self.assertEqual(platform.target_cost_per_lead, 0.05)
    
    def test_profile_id_generation(self):
        """Test profile ID generation"""
        with patch('openai.OpenAI'), \
             patch('boto3.client'), \
             patch('boto3.resource'):
            
            platform = LinkedInAutomationPlatform(self.mock_openai_key)
            profile_id = platform._generate_profile_id(self.test_profile)
            
            self.assertIsInstance(profile_id, str)
            self.assertEqual(len(profile_id), 32)  # MD5 hash length
            
            # Same profile should generate same ID
            profile_id_2 = platform._generate_profile_id(self.test_profile)
            self.assertEqual(profile_id, profile_id_2)
    
    def test_encryption_decryption(self):
        """Test data encryption and decryption for GDPR compliance"""
        with patch('openai.OpenAI'), \
             patch('boto3.client'), \
             patch('boto3.resource'):
            
            platform = LinkedInAutomationPlatform(self.mock_openai_key)
            
            test_data = "Sensitive profile information"
            encrypted = platform._encrypt_data(test_data)
            decrypted = platform._decrypt_data(encrypted)
            
            self.assertNotEqual(test_data, encrypted)
            self.assertEqual(test_data, decrypted)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_cached_icebreaker_retrieval(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test cached icebreaker retrieval"""
        # Mock DynamoDB with cached item
        mock_table = Mock()
        cached_item = {
            'Item': {
                'profile_id': 'test-profile-id',
                'icebreaker': 'encrypted-icebreaker',
                'tokens_used': 45,
                'cost': 0.000225,
                'created_at': datetime.now().isoformat()
            }
        }
        mock_table.get_item.return_value = cached_item
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        
        # Mock decryption
        with patch.object(platform, '_decrypt_data', return_value="Hi Jane, cached icebreaker!"):
            result = platform.generate_icebreaker(self.test_profile)
            
            self.assertTrue(result.cached)
            self.assertEqual(result.icebreaker, "Hi Jane, cached icebreaker!")
            self.assertEqual(result.tokens_used, 45)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_rate_limiting(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test LinkedIn rate limiting functionality"""
        # Mock DynamoDB rate limit table
        mock_rate_table = Mock()
        mock_rate_table.get_item.return_value = {
            'Item': {
                'date': datetime.now().date().isoformat(),
                'message_count': 49
            }
        }
        
        mock_icebreaker_table = Mock()
        mock_icebreaker_table.get_item.return_value = {}
        
        def mock_table_selector(table_name):
            if 'rate_limits' in table_name:
                return mock_rate_table
            else:
                return mock_icebreaker_table
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = mock_table_selector
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        
        # Should allow message (under limit)
        self.assertTrue(platform._check_rate_limit())
        self.assertEqual(platform.message_count_today, 49)
        
        # Mock exceeding limit
        mock_rate_table.get_item.return_value = {
            'Item': {
                'date': datetime.now().date().isoformat(),
                'message_count': 50
            }
        }
        
        # Should block message (at limit)
        self.assertFalse(platform._check_rate_limit())
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_unipile_mock_api_call(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test mock Unipile API call"""
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        
        test_message = "Hi Jane, your AI work at Tech Corp is inspiring!"
        result = platform.send_message_via_unipile(self.test_profile, test_message)
        
        self.assertTrue(result['success'])
        self.assertIn('message_id', result)
        self.assertEqual(result['recipient'], "Jane Doe")
        self.assertEqual(result['status'], 'sent')
        self.assertIn('sent_at', result)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_complete_outreach_process(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test complete outreach process"""
        # Mock OpenAI
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hi Jane, your AI work at Tech Corp is inspiring!"
        mock_response.usage.total_tokens = 50
        mock_openai_instance.chat.completions.create.return_value = mock_response
        
        # Mock DynamoDB tables
        mock_icebreaker_table = Mock()
        mock_icebreaker_table.get_item.return_value = {}  # No cached item
        mock_icebreaker_table.put_item.return_value = {}
        
        mock_rate_table = Mock()
        mock_rate_table.get_item.return_value = {}  # No existing rate limit
        mock_rate_table.put_item.return_value = {}
        
        def mock_table_selector(table_name):
            if 'rate_limits' in table_name:
                return mock_rate_table
            else:
                return mock_icebreaker_table
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = mock_table_selector
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        result = platform.process_outreach(self.test_profile)
        
        self.assertTrue(result['success'])
        self.assertIn('icebreaker', result)
        self.assertIn('cost', result)
        self.assertIn('unipile_response', result)
        self.assertEqual(result['message_count'], 1)
        self.assertEqual(result['remaining_messages'], 49)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_cost_optimization(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test cost optimization through caching"""
        # Mock OpenAI (should not be called for cached items)
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock DynamoDB with cached item
        mock_table = Mock()
        cached_item = {
            'Item': {
                'profile_id': 'test-profile-id',
                'icebreaker': 'encrypted-cached-message',
                'tokens_used': 45,
                'cost': 0.000225,
                'created_at': datetime.now().isoformat()
            }
        }
        mock_table.get_item.return_value = cached_item
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        
        # Mock decryption
        with patch.object(platform, '_decrypt_data', return_value="Cached message"):
            result = platform.generate_icebreaker(self.test_profile)
            
            # OpenAI should not have been called
            mock_openai_instance.chat.completions.create.assert_not_called()
            
            # Result should indicate it was cached
            self.assertTrue(result.cached)
            self.assertEqual(result.cost, 0.000225)
    
    def test_prompt_creation(self):
        """Test icebreaker prompt creation"""
        with patch('openai.OpenAI'), \
             patch('boto3.client'), \
             patch('boto3.resource'):
            
            platform = LinkedInAutomationPlatform(self.mock_openai_key)
            prompt = platform._create_icebreaker_prompt(self.test_profile)
            
            self.assertIn("Jane Doe", prompt)
            self.assertIn("AI Engineer", prompt)
            self.assertIn("Tech Corp", prompt)
            self.assertIn("personalized", prompt.lower())
            self.assertIn("professional", prompt.lower())
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_cloudwatch_logging(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test CloudWatch logging functionality"""
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        
        # Test logging
        platform._log_to_cloudwatch(
            'test_event', 
            'test-profile-id', 
            {'additional_data': 'test_value'}
        )
        
        # Verify CloudWatch was called
        mock_cloudwatch.put_metric_data.assert_called_once()
        call_args = mock_cloudwatch.put_metric_data.call_args
        
        self.assertEqual(call_args[1]['Namespace'], 'GTMotion/LinkedInAutomation')
        self.assertEqual(call_args[1]['MetricData'][0]['MetricName'], 'test_event')
        self.assertEqual(call_args[1]['MetricData'][0]['Value'], 1)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_daily_stats(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test daily statistics reporting"""
        # Mock DynamoDB rate limit table
        mock_rate_table = Mock()
        mock_rate_table.get_item.return_value = {
            'Item': {
                'date': datetime.now().date().isoformat(),
                'message_count': 25
            }
        }
        
        mock_icebreaker_table = Mock()
        
        def mock_table_selector(table_name):
            if 'rate_limits' in table_name:
                return mock_rate_table
            else:
                return mock_icebreaker_table
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.side_effect = mock_table_selector
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        stats = platform.get_daily_stats()
        
        self.assertEqual(stats['messages_sent'], 25)
        self.assertEqual(stats['remaining_messages'], 25)
        self.assertIn('estimated_cost', stats)
        self.assertIn('cost_per_lead', stats)
        self.assertIn('within_budget', stats)


class TestLambdaFunction(unittest.TestCase):
    """Test cases for AWS Lambda function"""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key', 'AWS_REGION': 'us-east-1'})
    @patch('linkedin_automation_platform.LinkedInAutomationPlatform')
    def test_lambda_process_outreach(self, mock_platform_class):
        """Test Lambda function for process outreach"""
        from lambda_function import lambda_handler
        
        # Mock platform instance
        mock_platform = Mock()
        mock_platform.process_outreach.return_value = {
            'success': True,
            'icebreaker': 'Test icebreaker',
            'cost': 0.0025,
            'cached': False
        }
        mock_platform_class.return_value = mock_platform
        
        # Test event
        event = {
            "action": "process_outreach",
            "profile": {
                "name": "Jane Doe",
                "title": "AI Engineer",
                "company": "Tech Corp"
            }
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 200)
        
        body = json.loads(result['body'])
        self.assertTrue(body['success'])
        self.assertIn('data', body)
        self.assertIn('timestamp', body)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key', 'AWS_REGION': 'us-east-1'})
    @patch('linkedin_automation_platform.LinkedInAutomationPlatform')
    def test_lambda_get_stats(self, mock_platform_class):
        """Test Lambda function for getting stats"""
        from lambda_function import lambda_handler
        
        # Mock platform instance
        mock_platform = Mock()
        mock_platform.get_daily_stats.return_value = {
            'messages_sent': 10,
            'estimated_cost': 0.025,
            'cost_per_lead': 0.0025
        }
        mock_platform_class.return_value = mock_platform
        
        # Test event
        event = {"action": "get_stats"}
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 200)
        
        body = json.loads(result['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['messages_sent'], 10)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key', 'AWS_REGION': 'us-east-1'})
    def test_lambda_invalid_action(self):
        """Test Lambda function with invalid action"""
        from lambda_function import lambda_handler
        
        event = {"action": "invalid_action"}
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result['statusCode'], 400)
        
        body = json.loads(result['body'])
        self.assertFalse(body['success'])
        self.assertIn('error', body)


def run_performance_tests():
    """Run performance tests for cost optimization"""
    print("\n" + "="*50)
    print("PERFORMANCE & COST OPTIMIZATION TESTS")
    print("="*50)
    
    # Simulate cost calculations
    tokens_per_message = [45, 67, 52, 73, 38, 61, 49, 58]
    cost_per_1k_tokens = 0.005
    target_cost_per_lead = 0.05
    
    total_tokens = sum(tokens_per_message)
    total_cost = (total_tokens / 1000) * cost_per_1k_tokens
    avg_cost_per_lead = total_cost / len(tokens_per_message)
    
    print(f"Messages processed: {len(tokens_per_message)}")
    print(f"Total tokens used: {total_tokens}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Average cost per lead: ${avg_cost_per_lead:.4f}")
    print(f"Target cost per lead: ${target_cost_per_lead:.4f}")
    print(f"Within budget: {'✅' if avg_cost_per_lead <= target_cost_per_lead else '❌'}")
    
    # Simulate caching benefits
    cache_hit_rate = 0.3  # 30% cache hit rate
    cached_messages = int(len(tokens_per_message) * cache_hit_rate)
    new_messages = len(tokens_per_message) - cached_messages
    
    cost_with_caching = (sum(tokens_per_message[:new_messages]) / 1000) * cost_per_1k_tokens
    savings = total_cost - cost_with_caching
    savings_percentage = (savings / total_cost) * 100
    
    print(f"\nWith 30% cache hit rate:")
    print(f"New messages: {new_messages}")
    print(f"Cached messages: {cached_messages}")
    print(f"Cost with caching: ${cost_with_caching:.4f}")
    print(f"Savings: ${savings:.4f} ({savings_percentage:.1f}%)")


if __name__ == '__main__':
    # Run unit tests
    print("Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance tests
    run_performance_tests()')
    def test_icebreaker_generation(self, mock_boto_resource, mock_boto_client, mock_openai):
        """Test icebreaker generation with GPT-4o"""
        # Mock OpenAI response
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hi Jane, your AI work at Tech Corp is inspiring!"
        mock_response.usage.total_tokens = 50
        
        mock_openai_instance.chat.completions.create.return_value = mock_response
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No cached item
        mock_table.put_item.return_value = {}
        
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Mock CloudWatch
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        platform = LinkedInAutomationPlatform(self.mock_openai_key)
        result = platform.generate_icebreaker(self.test_profile)
        
        self.assertIsInstance(result, IcebreakerResult)
        self.assertEqual(result.icebreaker, "Hi Jane, your AI work at Tech Corp is inspiring!")
        self.assertEqual(result.tokens_used, 50)
        self.assertEqual(result.cost, 0.00025)  # 50 tokens * $0.005/1000
        self.assertFalse(result.cached)
    
    @patch('openai.OpenAI')
    @patch('boto3.client')
    @patch('boto3.resource
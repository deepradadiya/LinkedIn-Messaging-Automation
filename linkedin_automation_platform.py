#!/usr/bin/env python3
"""
GTMotion.ai LinkedIn Automation Platform
Main application for AI-driven LinkedIn messaging automation
"""

import json
import boto3
import openai
import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from cryptography.fernet import Fernet
import requests
import time
from decimal import Decimal  # ✅ FIXED: import Decimal for DynamoDB compatibility

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LinkedInProfile:
    name: str
    title: str
    company: str
    industry: Optional[str] = None
    location: Optional[str] = None

@dataclass
class IcebreakerResult:
    profile_id: str
    icebreaker: str
    tokens_used: int
    cost: float
    generated_at: datetime
    cached: bool = False

class LinkedInAutomationPlatform:
    def __init__(self, openai_api_key: str, aws_region: str = 'us-east-1'):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.aws_region = aws_region
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=aws_region)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.daily_message_limit = 50
        self.message_count_today = 0
        self.last_reset_date = datetime.now().date()
        self.cost_per_1k_tokens = 0.005
        self.target_cost_per_lead = 0.05
        self.icebreaker_table_name = 'linkedin_icebreakers'
        self.rate_limit_table_name = 'linkedin_rate_limits'
        self._setup_dynamodb_tables()

    def _get_or_create_encryption_key(self) -> bytes:
        key_file = 'encryption_key.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    def _setup_dynamodb_tables(self):
        try:
            self.icebreaker_table = self.dynamodb.Table(self.icebreaker_table_name)
            self.icebreaker_table.load()
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            self._create_icebreaker_table()

        try:
            self.rate_limit_table = self.dynamodb.Table(self.rate_limit_table_name)
            self.rate_limit_table.load()
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            self._create_rate_limit_table()

    def _create_icebreaker_table(self):
        table = self.dynamodb.create_table(
            TableName=self.icebreaker_table_name,
            KeySchema=[{'AttributeName': 'profile_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'profile_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        self.icebreaker_table = table
        logger.info(f"Created DynamoDB table: {self.icebreaker_table_name}")

    def _create_rate_limit_table(self):
        table = self.dynamodb.create_table(
            TableName=self.rate_limit_table_name,
            KeySchema=[{'AttributeName': 'date', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'date', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        self.rate_limit_table = table
        logger.info(f"Created DynamoDB table: {self.rate_limit_table_name}")

    def _generate_profile_id(self, profile: LinkedInProfile) -> str:
        profile_string = f"{profile.name}_{profile.title}_{profile.company}"
        return hashlib.md5(profile_string.encode()).hexdigest()

    def _encrypt_data(self, data: str) -> str:
        return self.cipher_suite.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str) -> str:
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()

    def _check_rate_limit(self) -> bool:
        today = datetime.now().date().isoformat()
        try:
            response = self.rate_limit_table.get_item(Key={'date': today})
            if 'Item' in response:
                current_count = response['Item']['message_count']
                if current_count >= self.daily_message_limit:
                    logger.warning(f"Daily message limit reached: {current_count}/{self.daily_message_limit}")
                    return False
                self.message_count_today = current_count
            else:
                self.message_count_today = 0
            return True
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False

    def _update_rate_limit(self):
        today = datetime.now().date().isoformat()
        self.message_count_today += 1
        try:
            self.rate_limit_table.put_item(Item={
                'date': today,
                'message_count': self.message_count_today,
                'updated_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error updating rate limit: {str(e)}")

    def _get_cached_icebreaker(self, profile_id: str) -> Optional[IcebreakerResult]:
        try:
            response = self.icebreaker_table.get_item(Key={'profile_id': profile_id})
            if 'Item' in response:
                item = response['Item']
                cached_time = datetime.fromisoformat(item['created_at'])
                if datetime.now() - cached_time < timedelta(hours=24):
                    decrypted_icebreaker = self._decrypt_data(item['icebreaker'])
                    return IcebreakerResult(
                        profile_id=profile_id,
                        icebreaker=decrypted_icebreaker,
                        tokens_used=int(item['tokens_used']),
                        cost=float(item['cost']),
                        generated_at=cached_time,
                        cached=True
                    )
            return None
        except Exception as e:
            logger.error(f"Error retrieving cached icebreaker: {str(e)}")
            return None

    def _cache_icebreaker(self, result: IcebreakerResult, profile: LinkedInProfile):
        try:
            encrypted_icebreaker = self._encrypt_data(result.icebreaker)
            encrypted_profile_data = self._encrypt_data(json.dumps({
                'name': profile.name,
                'title': profile.title,
                'company': profile.company
            }))
            self.icebreaker_table.put_item(Item={
                'profile_id': result.profile_id,
                'icebreaker': encrypted_icebreaker,
                'profile_data': encrypted_profile_data,
                'tokens_used': Decimal(result.tokens_used),
                'cost': Decimal(str(result.cost)),  # ✅ FIXED: use Decimal for DynamoDB
                'created_at': result.generated_at.isoformat(),
                'ttl': int((datetime.now() + timedelta(hours=24)).timestamp())
            })
            logger.info(f"Cached icebreaker for profile {result.profile_id}")
        except Exception as e:
            logger.error(f"Error caching icebreaker: {str(e)}")

    def generate_icebreaker(self, profile: LinkedInProfile) -> IcebreakerResult:
        profile_id = self._generate_profile_id(profile)
        cached_result = self._get_cached_icebreaker(profile_id)
        if cached_result:
            logger.info(f"Using cached icebreaker for profile {profile_id}")
            self._log_to_cloudwatch('icebreaker_cache_hit', profile_id)
            return cached_result
        try:
            prompt = self._create_icebreaker_prompt(profile)
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert LinkedIn outreach specialist. Create personalized, professional, and engaging icebreaker messages that are concise (1-2 sentences) and likely to get a positive response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            icebreaker = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            cost = (tokens_used / 1000) * self.cost_per_1k_tokens
            result = IcebreakerResult(
                profile_id=profile_id,
                icebreaker=icebreaker,
                tokens_used=tokens_used,
                cost=cost,
                generated_at=datetime.now()
            )
            self._cache_icebreaker(result, profile)
            self._log_to_cloudwatch('icebreaker_generated', profile_id, {
                'tokens_used': tokens_used,
                'cost': cost,
                'profile_name': profile.name
            })
            logger.info(f"Generated icebreaker for {profile.name} - Cost: ${cost:.4f}")
            return result
        except Exception as e:
            logger.error(f"Error generating icebreaker: {str(e)}")
            self._log_to_cloudwatch('icebreaker_error', profile_id, {'error': str(e)})
            raise

    def _create_icebreaker_prompt(self, profile: LinkedInProfile) -> str:
        return f"""
        Create a personalized LinkedIn icebreaker message for the following profile:
        Name: {profile.name}
        Job Title: {profile.title}
        Company: {profile.company}
        
        Requirements:
        - Keep it concise (1-2 sentences)
        - Be professional and engaging
        - Reference their role or company
        - Avoid being overly salesy
        - Make it feel personal and genuine
        
        Example format: "Hi [Name], I noticed your work as [Title] at [Company] and found your approach to [relevant topic] really interesting!"
        """

    def send_message_via_unipile(self, profile: LinkedInProfile, message: str) -> Dict:
        mock_response = {
            'success': True,
            'message_id': f"msg_{int(time.time())}",
            'status': 'sent',
            'recipient': profile.name,
            'sent_at': datetime.now().isoformat(),
            'message_content': message[:50] + '...' if len(message) > 50 else message
        }
        logger.info(f"Mock Unipile API call - Sent message to {profile.name}")
        self._log_to_cloudwatch('message_sent', self._generate_profile_id(profile), {
            'recipient': profile.name,
            'message_preview': message[:50],
            'unipile_message_id': mock_response['message_id']
        })
        return mock_response

    def process_outreach(self, profile: LinkedInProfile) -> Dict:
        try:
            if not self._check_rate_limit():
                return {
                    'success': False,
                    'error': 'Daily message limit exceeded',
                    'limit': self.daily_message_limit,
                    'current_count': self.message_count_today
                }
            icebreaker_result = self.generate_icebreaker(profile)
            send_result = self.send_message_via_unipile(profile, icebreaker_result.icebreaker)
            self._update_rate_limit()
            self._log_to_cloudwatch('outreach_completed', icebreaker_result.profile_id, {
                'profile_name': profile.name,
                'cost': icebreaker_result.cost,
                'cached': icebreaker_result.cached,
                'message_count': self.message_count_today
            })
            return {
                'success': True,
                'profile_id': icebreaker_result.profile_id,
                'icebreaker': icebreaker_result.icebreaker,
                'cost': icebreaker_result.cost,
                'cached': icebreaker_result.cached,
                'tokens_used': icebreaker_result.tokens_used,
                'unipile_response': send_result,
                'message_count': self.message_count_today,
                'remaining_messages': self.daily_message_limit - self.message_count_today
            }
        except Exception as e:
            logger.error(f"Error in outreach process: {str(e)}")
            self._log_to_cloudwatch('outreach_error', 'unknown', {'error': str(e)})
            return {'success': False, 'error': str(e)}

    def _log_to_cloudwatch(self, event_type: str, profile_id: str, additional_data: Dict = None):
        try:
            metric_data = {
                'event_type': event_type,
                'profile_id': profile_id,
                'timestamp': datetime.now().isoformat(),
                'message_count': self.message_count_today
            }
            if additional_data:
                metric_data.update(additional_data)
            self.cloudwatch.put_metric_data(
                Namespace='GTMotion/LinkedInAutomation',
                MetricData=[{
                    'MetricName': event_type,
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [{
                        'Name': 'ProfileId',
                        'Value': profile_id
                    }]
                }]
            )
            logger.info(f"Logged to CloudWatch: {event_type} for profile {profile_id}")
        except Exception as e:
            logger.error(f"Error logging to CloudWatch: {str(e)}")

    def get_daily_stats(self) -> Dict:
        today = datetime.now().date().isoformat()
        try:
            rate_response = self.rate_limit_table.get_item(Key={'date': today})
            message_count = rate_response.get('Item', {}).get('message_count', 0)
            avg_tokens_per_message = 75
            estimated_daily_cost = (message_count * avg_tokens_per_message / 1000) * self.cost_per_1k_tokens
            return {
                'date': today,
                'messages_sent': message_count,
                'remaining_messages': self.daily_message_limit - message_count,
                'estimated_cost': estimated_daily_cost,
                'cost_per_lead': estimated_daily_cost / max(message_count, 1),
                'within_budget': estimated_daily_cost <= (self.target_cost_per_lead * message_count)
            }
        except Exception as e:
            logger.error(f"Error getting daily stats: {str(e)}")
            return {'error': str(e)}

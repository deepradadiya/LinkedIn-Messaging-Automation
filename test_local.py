#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from linkedin_automation_platform import LinkedInAutomationPlatform, LinkedInProfile

# Load environment variables
load_dotenv()

def test_local_setup():
    """Test the platform locally without AWS"""
    print("🚀 Testing GTMotion.ai LinkedIn Automation Platform")
    print("=" * 60)
    
    # Check if OpenAI key is set
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key or openai_key == 'your_openai_api_key_here':
        print("❌ Please set your OPENAI_API_KEY in the .env file")
        return
    
    try:
        # Initialize platform (will work without AWS for icebreaker generation)
        print("✅ Initializing platform...")
        platform = LinkedInAutomationPlatform(
            openai_api_key=openai_key,
            aws_region='us-east-1'
        )
        
        # Test profile
        test_profile = LinkedInProfile(
            name="Sarah Johnson",
            title="Data Scientist",
            company="Microsoft",
            industry="Technology",
            location="Seattle, WA"
        )
        
        print(f"✅ Testing with profile: {test_profile.name}")
        
        # Generate icebreaker (this will work without AWS)
        print("🔄 Generating icebreaker...")
        result = platform.generate_icebreaker(test_profile)
        
        print("✅ Success! Generated icebreaker:")
        print(f"   Profile: {test_profile.name}")
        print(f"   Message: {result.icebreaker}")
        print(f"   Cost: ${result.cost:.4f}")
        print(f"   Tokens: {result.tokens_used}")
        
        print("\n🎉 Local setup working correctly!")
        print("💡 Next steps: Set up AWS for production deployment")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Check your OpenAI API key and internet connection")

if __name__ == "__main__":
    test_local_setup()
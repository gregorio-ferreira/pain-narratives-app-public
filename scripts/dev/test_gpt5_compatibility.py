"""
Test GPT-5 model compatibility with our OpenAI client.
"""

import logging

from pain_narratives.core.openai_client import OpenAIClient


def test_basic_gpt5_functionality():
    """Test basic GPT-5 functionality with our client."""
    
    print("🔧 Testing GPT-5 Model Compatibility")
    print("=" * 50)
    
    try:
        client = OpenAIClient()
        
        # Test with simple messages like your example
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Please respond with a simple greeting."}
        ]
        
        print("📝 Testing gpt-5 model...")
        print(f"Messages: {messages}")
        
        # Test with minimal parameters first
        response = client.create_completion(
            messages=messages,
            model="gpt-5",
            temperature=1.0,  # Use default temperature for GPT-5
            max_tokens=100
        )
        
        print("✅ GPT-5 Response received:")
        if "choices" in response and response["choices"]:
            content = response["choices"][0]["message"]["content"]
            print(f"Content: '{content}'")
            print(f"Content length: {len(content)}")
            
            if not content.strip():
                print("⚠️  WARNING: Response content is empty!")
            else:
                print("✅ Response content looks good!")
        else:
            print("❌ No choices in response")
            print(f"Response keys: {list(response.keys())}")
        
    except Exception as e:
        print(f"❌ GPT-5 test failed: {e}")
        logging.error(f"GPT-5 test failed: {e}", exc_info=True)


def test_gpt5_mini_functionality():
    """Test GPT-5-mini model functionality."""
    
    print("\n🔧 Testing GPT-5-mini Model")
    print("=" * 50)
    
    try:
        client = OpenAIClient()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from GPT-5-mini!'"}
        ]
        
        print("📝 Testing gpt-5-mini model...")
        
        response = client.create_completion(
            messages=messages,
            model="gpt-5-mini",
            temperature=1.0,
            max_tokens=50
        )
        
        print("✅ GPT-5-mini Response received:")
        if "choices" in response and response["choices"]:
            content = response["choices"][0]["message"]["content"]
            print(f"Content: '{content}'")
            print(f"Content length: {len(content)}")
            
            if not content.strip():
                print("⚠️  WARNING: Response content is empty!")
            else:
                print("✅ Response content looks good!")
        else:
            print("❌ No choices in response")
        
    except Exception as e:
        print(f"❌ GPT-5-mini test failed: {e}")


def test_with_your_example():
    """Test using your exact example but with our client."""
    
    print("\n🔧 Testing with Your Example Format")
    print("=" * 50)
    
    try:
        from openai import OpenAI

        # Use raw OpenAI client like your example
        client = OpenAI()
        
        print("📝 Testing with raw OpenAI client...")
        
        completion = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},  # Changed from developer
                {"role": "user", "content": "Hello!"}
            ]
        )
        
        print("✅ Raw OpenAI Response received:")
        print(f"Message: {completion.choices[0].message}")
        print(f"Content: '{completion.choices[0].message.content}'")
        
    except Exception as e:
        print(f"❌ Raw OpenAI test failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting GPT-5 Compatibility Tests")
    print("=" * 60)
    
    test_basic_gpt5_functionality()
    test_gpt5_mini_functionality()
    test_with_your_example()
    
    print("\n✨ All tests completed!")    print("\n✨ All tests completed!")
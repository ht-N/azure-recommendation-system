"""
Test script for Azure OpenAI connection
"""
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

def test_openai_import():
    """Test if OpenAI can be imported"""
    try:
        from openai import AzureOpenAI
        print("✓ Successfully imported AzureOpenAI")
        return True
    except ImportError as e:
        print(f"✗ Failed to import AzureOpenAI: {e}")
        return False

def test_openai_init():
    """Test if AzureOpenAI can be initialized"""
    try:
        from openai import AzureOpenAI
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_CHAT_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        
        print(f"Endpoint: {endpoint}")
        print(f"API Key length: {len(api_key) if api_key else 'None'}")
        print(f"API Version: {api_version}")
        
        if not endpoint or not api_key:
            print("✗ Missing required environment variables")
            return False
        
        # Try different initialization methods
        try:
            # Method 1: Standard initialization
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            print("✓ Successfully initialized Azure OpenAI client (Method 1)")
            return True
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            
            try:
                # Method 2: Without api_version
                client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key
                )
                print("✓ Successfully initialized Azure OpenAI client (Method 2)")
                return True
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
                
                try:
                    # Method 3: Using different parameter names
                    client = AzureOpenAI(
                        endpoint=endpoint,
                        api_key=api_key,
                        version=api_version
                    )
                    print("✓ Successfully initialized Azure OpenAI client (Method 3)")
                    return True
                except Exception as e3:
                    print(f"Method 3 failed: {e3}")
                    raise e1  # Raise the original error
        
    except Exception as e:
        print(f"✗ Failed to initialize Azure OpenAI: {e}")
        return False

def test_chat_completion():
    """Test if chat completion works"""
    try:
        from openai import AzureOpenAI
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_CHAT_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4")
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "user", "content": "Hello, this is a test message."}
            ],
            max_tokens=10
        )
        
        print("✓ Successfully called chat completion")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to call chat completion: {e}")
        return False

if __name__ == "__main__":
    print("Testing Azure OpenAI connection...")
    print("=" * 50)
    
    # Test 1: Import
    print("Test 1: Import AzureOpenAI")
    import_success = test_openai_import()
    print()
    
    if import_success:
        # Test 2: Initialize
        print("Test 2: Initialize AzureOpenAI client")
        init_success = test_openai_init()
        print()
        
        if init_success:
            # Test 3: Chat completion
            print("Test 3: Call chat completion")
            completion_success = test_chat_completion()
            print()
            
            if completion_success:
                print("✓ All tests passed!")
            else:
                print("✗ Chat completion test failed")
        else:
            print("✗ Initialization test failed")
    else:
        print("✗ Import test failed")
    
    print("=" * 50)

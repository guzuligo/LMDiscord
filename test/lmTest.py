"""
Hello World script to test connection with LM Studio.

LM Studio runs a local OpenAI-compatible API server (default: http://localhost:1234/v1).
This script sends a simple message and prints the response.

Prerequisites:
    - LM Studio must be running with a model loaded
    - The local server should be active on port 1234

Usage:
    pip install openai
    python lmTest.py
"""

from openai import OpenAI


def main():
    # Point to LM Studio's local server
    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed"  # LM Studio doesn't require authentication
    )

    # Send a simple hello world message
    print("Sending request to LM Studio...")
    response = client.chat.completions.create(
        model="local-model",  # LM Studio accepts any model name
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Please introduce yourself in one sentence."}
        ],
        max_tokens=2500,
        temperature=0.7
    )

    # Print the response
    print("\nResponse from LM Studio:")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
"""
Hello World script to test LM Studio tool calling (function calling).

This script defines a simple "add_numbers" tool and demonstrates the full
tool-calling loop: request with tools → model returns tool_calls → execute
the function → send result back → get final response.

Prerequisites:
    - LM Studio must be running with a model that supports function/tool calling
    - The local server should be active on port 1234

Usage:
    .venv/bin/python lmTest_2.py
"""

import json
import base64
import io
from pathlib import Path
from openai import OpenAI
from PIL import Image


# ---------------------------------------------------------------------------
# Tool / Function Definitions
# ---------------------------------------------------------------------------

# MIME type mapping for image file extensions
IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Add two numbers together and return the sum.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The first number."
                    },
                    "b": {
                        "type": "number",
                        "description": "The second number."
                    }
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "describe_image",
            "description": "Read an image file from a given path and return it as base64 data with MIME type for the model to analyze and describe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "The full file path to the image file."
                    }
                },
                "required": ["image_path"]
            }
        }
    }
]

# Registry of executable functions (name → callable)
FUNCTIONS = {
    "add_numbers": lambda a, b: a + b,
}


def _get_image_mime_type(file_path: str) -> str:
    """Determine the MIME type of an image file based on its extension."""
    ext = Path(file_path).suffix.lower()
    return IMAGE_MIME_TYPES.get(ext, "application/octet-stream")


def _process_image_for_vision(image_path: str, max_dimension: int = 768, quality: int = 85) -> tuple:
    """Load an image with Pillow, resize if needed, and return (base64_string, mime_type).
    
    Similar to browser_screenshot: resizes the image to keep it manageable for the model's
    context window, and compresses as JPEG to reduce size.
    
    Args:
        image_path: Path to the image file
        max_dimension: Maximum width or height in pixels (default: 768)
        quality: JPEG quality 1-100 (default: 85)
    
    Returns:
    Tuple of (base64_string, mime_type)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Open image with Pillow
    img = Image.open(path)
    
    # Convert RGBA to RGB if needed (JPEG doesn't support alpha)
    if img.mode == "RGBA":
        # Create white background
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # Resize if image is larger than max_dimension
    orig_width, orig_height = img.size
    if max(orig_width, orig_height) > max_dimension:
        ratio = max_dimension / max(orig_width, orig_height)
        new_width = max(320, int(orig_width * ratio))
        new_height = max(200, int(orig_height * ratio))
        img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Save as JPEG to compressed bytes
    output_buf = io.BytesIO()
    img.save(output_buf, format="JPEG", quality=quality, optimize=True)
    compressed_bytes = output_buf.getvalue()
    
    # Encode to base64
    base64_data = base64.b64encode(compressed_bytes).decode("utf-8")
    
    return base64_data, "image/jpeg"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def execute_tool_call(function_name: str, arguments: dict) -> dict:
    """Execute a tool call and return the result.
    
    Returns a dict with either:
    - {"type": "text", "content": <json_string>} for regular tools
    - {"type": "image", "base64_data": <str>, "mime_type": <str>} for describe_image
    """
    if function_name == "describe_image":
        image_path = arguments.get("image_path", "")
        try:
            base64_data, mime_type = _process_image_for_vision(image_path)
            return {
                "type": "image",
                "base64_data": base64_data,
                "mime_type": mime_type,
            }
        except Exception as exc:
            return {"type": "text", "content": json.dumps({"error": str(exc)})}
    
    func = FUNCTIONS.get(function_name)
    if func is None:
        return {"type": "text", "content": json.dumps({"error": f"Unknown function: {function_name}"})}
    try:
        result = func(**arguments)
        return {"type": "text", "content": json.dumps({"result": result})}
    except Exception as exc:
        return {"type": "text", "content": json.dumps({"error": str(exc)})}


def build_messages_for_response(system_msg, user_msg, tool_call, tool_result_dict, has_image=False):
    """Build the messages list for sending tool results back to the model.
    
    If the tool returned an image, the image is embedded in a new user message
    after the tool response, so the vision model can analyze it.
    """
    if has_image:
        image_url = f"data:{tool_result_dict['mime_type']};base64,{tool_result_dict['base64_data']}"
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": "Image loaded successfully."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
    else:
        # Send text result as usual
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            },
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result_dict["content"]
            }
        ]
    
    return messages


def main():
    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="not-needed"
    )

    # Example prompts (change to test different scenarios):
    # Arithmetic test:
    # user_message = "Please calculate 42 + 138 for me."
    # Image description test:
    user_message = "Please describe the image at /run/media/user1/4TB/bkup/Documents/unholyDesireMixSinister_v70.jpg"

    print("Sending request to LM Studio with tool definitions...")
    print(f"User: {user_message}\n")

    # ----- Step 1: Send the user message along with tool definitions ----------
    response = client.chat.completions.create(
        model="local-model",
        messages=[
            {"role": "system", "content": "You are a helpful assistant. If the user asks you to describe an image, call the describe_image tool with the image path."},
            {"role": "user", "content": user_message}
        ],
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=2000,
        temperature=0.3
    )

    choice = response.choices[0]
    print(f"First response (finish_reason={choice.finish_reason}):")
    print(f"  Message content: {choice.message.content}\n")

    # ----- Step 2: If the model wants to call a tool, handle it ---------------
    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        for tool_call in choice.message.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"Tool call requested:")
            print(f"  Function: {func_name}")
            print(f"  Arguments: {args}\n")

            # Execute the function locally (returns structured dict now)
            tool_result = execute_tool_call(func_name, args)
            
            # Check if this is an image tool
            is_image_tool = tool_result.get("type") == "image"
            
            if is_image_tool:
                print(f"Tool result: [Image data - {tool_result['mime_type']}]")
                print(f"  Base64 length: {len(tool_result['base64_data'])} characters\n")
            else:
                print(f"Tool result: {tool_result['content']}\n")

            # ----- Step 3: Send the tool result back to the model ---------------
            messages = build_messages_for_response(
                "You are a helpful assistant.",
                user_message,
                tool_call,
                tool_result,
                has_image=is_image_tool
            )

            # For image tools, we don't include tools= in the second call
            # since the model should respond directly with a description
            create_kwargs = {
                "model": "local-model",
                "messages": messages,
                "max_tokens": 5000,
                "temperature": 0.7,
            }
            if not is_image_tool:
                create_kwargs["tools"] = TOOLS

            response2 = client.chat.completions.create(**create_kwargs)

            final_message = response2.choices[0].message.content
            print("=" * 50)
            print("Final response from LM Studio:")
            print("=" * 50)
            print(final_message)
    else:
        print("No tool was called. Model responded directly:")
        print(choice.message.content)


if __name__ == "__main__":
    main()
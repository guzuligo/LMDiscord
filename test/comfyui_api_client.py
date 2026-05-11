#!/usr/bin/env python3
"""
ComfyUI API Client
Sends a workflow JSON to a local ComfyUI instance, polls for completion,
and downloads the generated images.

Requirements:
    pip install requests

Usage:
    python comfyui_api_client.py
    # Or customize paths/server in the script
"""

import json
import requests
import time
import uuid
import os
import sys

SERVER_ADDRESS = "http://localhost:8188"
OUTPUT_DIR = "output_images"

def send_workflow(workflow_data):
    """Send workflow to ComfyUI and return prompt_id."""
    client_id = str(uuid.uuid4())
    payload = {
        "prompt": workflow_data,
        "client_id": client_id
    }
    
    print(f"📤 Sending workflow to {SERVER_ADDRESS}...")
    try:
        response = requests.post(f"{SERVER_ADDRESS}/prompt", json=payload)
        response.raise_for_status()
        data = response.json()
        prompt_id = data.get("prompt_id")
        print(f"✅ Prompt sent successfully! ID: {prompt_id}")
        return prompt_id, client_id
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is ComfyUI running at the correct address?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to send prompt: {e}")
        sys.exit(1)

def wait_for_completion(prompt_id):
    """Poll ComfyUI history until the prompt finishes."""
    print("⏳ Waiting for generation to complete...")
    while True:
        try:
            resp = requests.get(f"{SERVER_ADDRESS}/history/{prompt_id}")
            resp.raise_for_status()
            history = resp.json()
            
            if prompt_id in history:
                print("✅ Generation complete!")
                return history[prompt_id]
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Error polling history: {e}")
            time.sleep(2)

def download_images(history_output):
    """Download generated images from ComfyUI output."""
    outputs = history_output.get('outputs', {})
    if not outputs:
        print("⚠️ No outputs found in history.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    image_count = 0
    
    for node_id, node_output in outputs.items():
        images = node_output.get('images', [])
        for img in images:
            filename = img.get('filename', '')
            subfolder = img.get('subfolder', '')
            img_type = img.get('type', 'output')
            
            download_url = f"{SERVER_ADDRESS}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
            save_path = os.path.join(OUTPUT_DIR, filename)
            
            try:
                img_resp = requests.get(download_url, stream=True)
                img_resp.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in img_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"💾 Saved: {save_path}")
                image_count += 1
            except Exception as e:
                print(f"❌ Failed to download {filename}: {e}")
                
    print(f"\n🎉 Done! {image_count} image(s) saved to '{OUTPUT_DIR}/'")

def main():
    json_path = "comfyui_RefToRef_api.json"
    
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}")
        sys.exit(1)
        
    print(f"📂 Loading workflow from: {json_path}")
    with open(json_path, 'r') as f:
        workflow = json.load(f)
        
    prompt_id, client_id = send_workflow(workflow)
    history = wait_for_completion(prompt_id)
    download_images(history)

if __name__ == "__main__":
    main()

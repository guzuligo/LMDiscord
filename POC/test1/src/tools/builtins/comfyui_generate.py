"""
ComfyUI Image Generation Tool

This module implements a tool for triggering image generation via ComfyUI API.
It sends workflow JSON to the ComfyUI server and handles the generation process.

Key Responsibilities:
- Send ComfyUI workflow JSON to the ComfyUI server
- Poll for generation completion
- Download generated images
- Handle async execution (long-running operation)
- Prevent duplicate generation requests

Tool Definition:
- name: "comfyui_generate"
- description: "Generate an image using ComfyUI"
- parameters: { prompt: str, workflow_json: dict (optional), output_path: str }
"""

# TODO: Implement ComfyUIGenerateTool class (extends BaseTool)
# - name: "comfyui_generate"
# - description: "Generate an image using ComfyUI image generation server"
# - parameters: { prompt: str, workflow_json: dict (optional), output_path: str }
# - execute(prompt, ...) -> send workflow to ComfyUI (localhost:8188), poll, download
# - Async tool: runs in background, returns progress status
# - Duplicate prevention: only one generation at a time
# - Use test/comfyui_api_client.py as reference
# - Use test/comfyui_RefToRef_api.json as workflow template
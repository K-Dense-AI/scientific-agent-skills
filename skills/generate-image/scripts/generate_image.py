#!/usr/bin/env python3
"""
Generate and edit images using OpenRouter API with various image generation models.

Supports models like:
- google/gemini-3.1-flash-image-preview (generation and editing)
- black-forest-labs/flux.2-pro (generation and editing)
- black-forest-labs/flux.2-flex (generation)
- And more image generation models available on OpenRouter

For image editing, provide an input image along with an editing prompt.
"""

import sys
import json
import base64
import argparse
import os
import time
from pathlib import Path
from typing import Any, Optional


ATLAS_CLOUD_API_BASE = "https://api.atlascloud.ai/api/v1"
ATLAS_CLOUD_GENERATE_MODEL = "google/nano-banana-2/text-to-image"
ATLAS_CLOUD_EDIT_MODEL = "google/nano-banana-2/edit"
OPENROUTER_DEFAULT_MODEL = "google/gemini-3.1-flash-image-preview"


def check_env_file(var_names: tuple[str, ...] = ("OPENROUTER_API_KEY",)) -> Optional[str]:
    """Check if .env file exists and contains one of the requested API keys."""
    # Look for .env in current directory and parent directories
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        env_file = parent / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    for var_name in var_names:
                        if line.startswith(f'{var_name}='):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            if api_key:
                                return api_key
    return None


def resolve_api_key(provider: str, explicit_key: Optional[str]) -> Optional[str]:
    """Resolve the API key for the selected provider."""
    if explicit_key:
        return explicit_key
    if provider == "atlascloud":
        return (
            os.getenv("ATLASCLOUD_API_KEY")
            or os.getenv("ATLAS_CLOUD_API_KEY")
            or check_env_file(("ATLASCLOUD_API_KEY", "ATLAS_CLOUD_API_KEY"))
        )
    return os.getenv("OPENROUTER_API_KEY") or check_env_file(("OPENROUTER_API_KEY",))


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and return it as a base64 data URL."""
    path = Path(image_path)
    if not path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    mime_type = mime_types.get(ext, 'image/png')
    
    with open(path, 'rb') as f:
        image_data = f.read()
    
    base64_data = base64.b64encode(image_data).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"


def save_base64_image(base64_data: str, output_path: str) -> None:
    """Save base64 encoded image to file."""
    # Remove data URL prefix if present
    if ',' in base64_data:
        base64_data = base64_data.split(',', 1)[1]

    # Decode and save
    image_data = base64.b64decode(base64_data)
    with open(output_path, 'wb') as f:
        f.write(image_data)


def save_image_output(output: Any, output_path: str) -> None:
    """Save an image output returned as a URL, data URL, or base64 string."""
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found. Install with: pip install requests")
        sys.exit(1)

    if isinstance(output, dict):
        for key in ("url", "download_url", "image_url"):
            if output.get(key):
                return save_image_output(output[key], output_path)
        for key in ("b64_json", "base64", "data"):
            if output.get(key):
                return save_image_output(output[key], output_path)

    if not isinstance(output, str):
        print(f"⚠️ Unexpected image output format: {output}")
        sys.exit(1)

    if output.startswith(("http://", "https://")):
        response = requests.get(output, timeout=300)
        if response.status_code != 200:
            print(f"❌ Failed to download generated image ({response.status_code}): {response.text[:300]}")
            sys.exit(1)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return

    save_base64_image(output, output_path)


def upload_atlas_image(api_key: str, image_path: str) -> str:
    """Upload a local image to Atlas Cloud and return the temporary media URL."""
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found. Install with: pip install requests")
        sys.exit(1)

    path = Path(image_path)
    if not path.exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)

    with open(path, "rb") as f:
        response = requests.post(
            f"{ATLAS_CLOUD_API_BASE}/model/uploadMedia",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (path.name, f)},
            timeout=120,
        )

    if response.status_code != 200:
        print(f"❌ Atlas Cloud upload error ({response.status_code}): {response.text}")
        sys.exit(1)

    payload = response.json()
    data = payload.get("data", payload)
    media_url = data.get("download_url") or data.get("url")
    if not media_url:
        print(f"❌ Atlas Cloud upload response did not include a media URL: {payload}")
        sys.exit(1)
    return media_url


def atlas_prediction_payload(response_json: dict[str, Any]) -> dict[str, Any]:
    data = response_json.get("data")
    return data if isinstance(data, dict) else response_json


def atlas_prediction_outputs(payload: dict[str, Any]) -> list[Any]:
    for key in ("outputs", "output", "result", "images", "urls"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if value:
            return [value]
    return []


def generate_image_atlascloud(
    prompt: str,
    model: str,
    output_path: str,
    api_key: str,
    input_image: Optional[str] = None,
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    output_format: str = "png",
    poll_interval: float = 3.0,
    timeout_seconds: float = 300.0,
) -> dict:
    """Generate or edit an image using Atlas Cloud's async Media API."""
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found. Install with: pip install requests")
        sys.exit(1)

    is_editing = input_image is not None
    if model == OPENROUTER_DEFAULT_MODEL:
        model = ATLAS_CLOUD_EDIT_MODEL if is_editing else ATLAS_CLOUD_GENERATE_MODEL

    if is_editing:
        print(f"✏️ Editing image with Atlas Cloud model: {model}")
        print(f"📷 Input image: {input_image}")
        image_url = upload_atlas_image(api_key, input_image)
    else:
        print(f"🎨 Generating image with Atlas Cloud model: {model}")
        image_url = None
    print(f"📝 Prompt: {prompt}")

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "output_format": output_format,
    }
    if image_url:
        body["images"] = [image_url]

    response = requests.post(
        f"{ATLAS_CLOUD_API_BASE}/model/generateImage",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=120,
    )

    if response.status_code != 200:
        print(f"❌ Atlas Cloud API Error ({response.status_code}): {response.text}")
        sys.exit(1)

    submitted = response.json()
    prediction = atlas_prediction_payload(submitted)
    prediction_id = prediction.get("id") or prediction.get("prediction_id")
    if not prediction_id:
        print(f"❌ Atlas Cloud response did not include a prediction ID: {submitted}")
        sys.exit(1)

    print(f"⏳ Atlas Cloud prediction: {prediction_id}")
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    interval = max(1.0, poll_interval)
    while time.monotonic() < deadline:
        poll_response = requests.get(
            f"{ATLAS_CLOUD_API_BASE}/model/prediction/{prediction_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        if poll_response.status_code != 200:
            print(f"❌ Atlas Cloud polling error ({poll_response.status_code}): {poll_response.text}")
            sys.exit(1)

        current = atlas_prediction_payload(poll_response.json())
        status = str(current.get("status") or "").lower()
        if status in {"completed", "succeeded", "success"}:
            outputs = atlas_prediction_outputs(current)
            if not outputs:
                print(f"❌ Atlas Cloud prediction completed without outputs: {current}")
                sys.exit(1)
            save_image_output(outputs[0], output_path)
            print(f"✅ Image saved to: {output_path}")
            return current
        if status in {"failed", "error", "canceled", "cancelled"}:
            print(f"❌ Atlas Cloud prediction failed: {json.dumps(current, indent=2)}")
            sys.exit(1)
        time.sleep(interval)

    print(f"❌ Atlas Cloud prediction timed out after {timeout_seconds:g}s: {prediction_id}")
    sys.exit(1)


def generate_image(
    prompt: str,
    model: str = OPENROUTER_DEFAULT_MODEL,
    output_path: str = "generated_image.png",
    api_key: Optional[str] = None,
    input_image: Optional[str] = None,
    provider: str = "openrouter",
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    output_format: str = "png",
    poll_interval: float = 3.0,
    timeout_seconds: float = 300.0,
) -> dict:
    """
    Generate or edit an image using OpenRouter or Atlas Cloud.

    Args:
        prompt: Text description of the image to generate, or editing instructions
        model: OpenRouter model ID (default: google/gemini-3.1-flash-image-preview)
        output_path: Path to save the generated image
        api_key: API key (will check .env if not provided)
        input_image: Path to an input image for editing (optional)
        provider: "openrouter" or "atlascloud"

    Returns:
        dict: Response from OpenRouter API
    """
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found. Install with: pip install requests")
        sys.exit(1)

    api_key = resolve_api_key(provider, api_key)

    if not api_key:
        if provider == "atlascloud":
            print("❌ Error: ATLASCLOUD_API_KEY or ATLAS_CLOUD_API_KEY not found!")
            print("\nSet it with:")
            print("export ATLASCLOUD_API_KEY=your-api-key-here")
            print("\nGet your API key from: https://www.atlascloud.ai/console/api-keys")
        else:
            print("❌ Error: OPENROUTER_API_KEY not found!")
            print("\nPlease create a .env file in your project directory with:")
            print("OPENROUTER_API_KEY=your-api-key-here")
            print("\nOr set the environment variable:")
            print("export OPENROUTER_API_KEY=your-api-key-here")
            print("\nGet your API key from: https://openrouter.ai/keys")
        sys.exit(1)

    if provider == "atlascloud":
        return generate_image_atlascloud(
            prompt=prompt,
            model=model,
            output_path=output_path,
            api_key=api_key,
            input_image=input_image,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            output_format=output_format,
            poll_interval=poll_interval,
            timeout_seconds=timeout_seconds,
        )

    # Determine if this is generation or editing
    is_editing = input_image is not None
    
    if is_editing:
        print(f"✏️ Editing image with model: {model}")
        print(f"📷 Input image: {input_image}")
        print(f"📝 Edit prompt: {prompt}")
        
        # Load input image as base64
        image_data_url = load_image_as_base64(input_image)
        
        # Build multimodal message content for image editing
        message_content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data_url
                }
            }
        ]
    else:
        print(f"🎨 Generating image with model: {model}")
        print(f"📝 Prompt: {prompt}")
        message_content = prompt

    # Make API request
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            "modalities": ["image", "text"]
        }
    )

    # Check for errors
    if response.status_code != 200:
        print(f"❌ API Error ({response.status_code}): {response.text}")
        sys.exit(1)

    result = response.json()

    # Extract and save image
    if result.get("choices"):
        message = result["choices"][0]["message"]

        # Handle both 'images' and 'content' response formats
        images = []

        if message.get("images"):
            images = message["images"]
        elif message.get("content"):
            # Some models return content as array with image parts
            content = message["content"]
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image":
                        images.append(part)

        if images:
            # Save the first image
            image = images[0]
            if "image_url" in image:
                image_url = image["image_url"]["url"]
                save_base64_image(image_url, output_path)
                print(f"✅ Image saved to: {output_path}")
            elif "url" in image:
                save_base64_image(image["url"], output_path)
                print(f"✅ Image saved to: {output_path}")
            else:
                print(f"⚠️ Unexpected image format: {image}")
        else:
            print("⚠️ No image found in response")
            if message.get("content"):
                print(f"Response content: {message['content']}")
    else:
        print("❌ No choices in response")
        print(f"Response: {json.dumps(result, indent=2)}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate or edit images using OpenRouter or Atlas Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with default model (Gemini 3.1 Flash Image Preview)
  python generate_image.py "A beautiful sunset over mountains"

  # Generate with Atlas Cloud Nano Banana 2
  python generate_image.py "A beautiful sunset over mountains" --provider atlascloud

  # Edit an image with Atlas Cloud Nano Banana 2
  python generate_image.py "Make the sky purple" --provider atlascloud --input photo.jpg --output edited.png

  # Use a specific model
  python generate_image.py "A cat in space" --model "black-forest-labs/flux.2-pro"

  # Specify output path
  python generate_image.py "Abstract art" --output my_image.png

  # Edit an existing image
  python generate_image.py "Make the sky purple" --input photo.jpg --output edited.png

  # Edit with a specific model
  python generate_image.py "Add a hat to the person" --input portrait.png -m "black-forest-labs/flux.2-pro"

Popular image models:
  - google/gemini-3.1-flash-image-preview (default, high quality, generation + editing)
  - black-forest-labs/flux.2-pro (fast, high quality, generation + editing)
  - black-forest-labs/flux.2-flex (development version)

Atlas Cloud default models:
  - google/nano-banana-2/text-to-image (generation)
  - google/nano-banana-2/edit (editing)
        """
    )

    parser.add_argument(
        "prompt",
        type=str,
        help="Text description of the image to generate, or editing instructions"
    )

    parser.add_argument(
        "--provider",
        choices=["openrouter", "atlascloud"],
        default="openrouter",
        help="Image provider (default: openrouter)"
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=OPENROUTER_DEFAULT_MODEL,
        help=(
            "Model ID. Defaults to OpenRouter's Gemini image model; with "
            "--provider atlascloud, this default maps to Nano Banana 2 generation/edit models."
        )
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="generated_image.png",
        help="Output file path (default: generated_image.png)"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input image path for editing (enables edit mode)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="Provider API key (will check environment and .env if not provided)"
    )

    parser.add_argument(
        "--aspect-ratio",
        choices=["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        default="1:1",
        help="Atlas Cloud aspect ratio (default: 1:1)"
    )

    parser.add_argument(
        "--resolution",
        choices=["1k", "2k", "4k"],
        default="1k",
        help="Atlas Cloud output resolution (default: 1k)"
    )

    parser.add_argument(
        "--output-format",
        choices=["default", "png", "jpeg"],
        default="png",
        help="Atlas Cloud output format (default: png)"
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="Seconds between Atlas Cloud prediction polls (default: 3)"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Maximum seconds to wait for Atlas Cloud prediction completion (default: 300)"
    )

    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        model=args.model,
        output_path=args.output,
        api_key=args.api_key,
        input_image=args.input,
        provider=args.provider,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        output_format=args.output_format,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    main()

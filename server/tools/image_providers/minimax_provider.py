import os
import base64
import traceback
from typing import Optional, Any
import httpx
from .image_base_provider import ImageProviderBase
from ..utils.image_utils import get_image_info_and_save, generate_image_id
from services.config_service import FILES_DIR, config_service


class MinimaxImageProvider(ImageProviderBase):
    """MiniMax image generation provider implementation"""

    async def generate(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        input_images: Optional[list[str]] = None,
        **kwargs: Any
    ) -> tuple[str, int, int, str]:
        config = config_service.app_config.get('minimax', {})
        api_key = str(config.get("api_key", ""))
        api_url = str(config.get("url", "https://api.minimaxi.com/v1/image_generation"))

        if not api_key:
            raise ValueError("MiniMax API key is not configured")

        print(f'🖼️ MiniMax Image Request - url: {api_url}, model: {model}, aspect_ratio: {aspect_ratio}')

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            # Check for API error
            base_resp = data.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                raise Exception(f"MiniMax API error: {base_resp.get('status_msg', 'unknown')}")

            inner_data = data.get("data") or {}
            image_urls = inner_data.get("image_urls", [])
            if not image_urls:
                raise Exception("No image data returned from MiniMax API")

            image_url = image_urls[0]
            print(f'🖼️ MiniMax got image URL, downloading...')
            image_id = generate_image_id()
            mime_type, width, height, extension = await get_image_info_and_save(
                image_url, os.path.join(FILES_DIR, f'{image_id}')
            )

            if mime_type is None:
                raise Exception('Failed to determine image MIME type')

            filename = f'{image_id}.{extension}'
            print(f'🖼️ MiniMax Image Success - {filename} ({width}x{height})')
            return mime_type, width, height, filename

        except Exception as e:
            print(f'🖼️ MiniMax Image Error - {e}')
            traceback.print_exc()
            raise e

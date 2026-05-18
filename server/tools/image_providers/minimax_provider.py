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
            "response_format": "base64",
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            print(f'🖼️ MiniMax API Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}')
            inner_data = data.get("data") if isinstance(data, dict) else None
            print(f'🖼️ MiniMax API data field: {type(inner_data)} - {str(inner_data)[:500] if inner_data else "None"}')
            image_base64_list = (inner_data or {}).get("image_base64", [])
            if not image_base64_list:
                raise Exception("No image data returned from MiniMax API")

            image_b64 = image_base64_list[0]
            image_id = generate_image_id()
            mime_type, width, height, extension = await get_image_info_and_save(
                image_b64, os.path.join(FILES_DIR, f'{image_id}'), is_b64=True
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

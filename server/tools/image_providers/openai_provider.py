import os
import json
import traceback
from typing import Optional, Any
import httpx
from .image_base_provider import ImageProviderBase
from ..utils.image_utils import get_image_info_and_save, generate_image_id
from services.config_service import FILES_DIR
from services.config_service import config_service


class OpenAIImageProvider(ImageProviderBase):
    """OpenAI image generation provider implementation with streaming support"""

    async def generate(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        input_images: Optional[list[str]] = None,
        **kwargs: Any
    ) -> tuple[str, int, int, str]:
        """
        Generate image using OpenAI API with streaming (partial_images)

        Returns:
            tuple[str, int, int, str]: (mime_type, width, height, filename)
        """

        config = config_service.app_config.get('openai', {})
        api_key = str(config.get("api_key", ""))
        base_url = str(config.get("url", "")).rstrip('/')

        if not api_key:
            raise ValueError("OpenAI API key is not configured")

        # Remove openai/ prefix if present
        model = model.replace('openai/', '')

        print(f'🖼️ OpenAI Image Provider (streaming) - base_url: {base_url}, model: {model}')
        print(f'🖼️ OpenAI Image Request - model: {model}, aspect_ratio: {aspect_ratio}, has_input_images: {bool(input_images)}')

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            if input_images and len(input_images) > 0:
                # Image editing mode - use images/edits endpoint
                # edits endpoint uses multipart/form-data, handle separately
                return await self._edit_image_streaming(
                    base_url, headers, api_key, model, prompt, input_images[0], **kwargs
                )
            else:
                # Image generation mode
                size_map = {
                    "1:1": "1024x1024",
                    "16:9": "1792x1024",
                    "9:16": "1024x1792",
                    "4:3": "1024x768",
                    "3:4": "768x1024"
                }
                size = size_map.get(aspect_ratio, "1024x1024")

                payload = {
                    "model": model,
                    "prompt": prompt,
                    "n": kwargs.get("num_images", 1),
                    "size": size,
                }

                return await self._non_stream_request(
                    f"{base_url}/images/generations", headers, payload
                )

        except Exception as e:
            print(f'🖼️ OpenAI Image Error - base_url: {base_url}, model: {model}, error: {e}')
            traceback.print_exc()
            raise e

    async def _edit_image_streaming(
        self,
        base_url: str,
        headers: dict,
        api_key: str,
        model: str,
        prompt: str,
        input_image_path: str,
        **kwargs: Any
    ) -> tuple[str, int, int, str]:
        """Handle image edit with streaming using multipart form data"""
        full_path = os.path.join(FILES_DIR, input_image_path)

        async with httpx.AsyncClient(timeout=300) as client:
            with open(full_path, 'rb') as image_file:
                files = {"image": image_file}
                data = {
                    "model": model,
                    "prompt": prompt,
                    "n": str(kwargs.get("num_images", 1)),
                }
                resp = await client.post(
                    f"{base_url}/images/edits",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()

        data_list = result.get("data", [])
        if not data_list:
            raise Exception("No image data returned from OpenAI API")
        image_item = data_list[0]
        return await self._save_image(image_item.get("b64_json"), image_item.get("url"))

    async def _non_stream_request(
        self, url: str, headers: dict, payload: dict
    ) -> tuple[str, int, int, str]:
        """Make a standard (non-streaming) request"""
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise Exception(
                    f"OpenAI API error {resp.status_code}: {resp.text}"
                )
            result = resp.json()

        data_list = result.get("data", [])
        if not data_list:
            raise Exception("No image data returned from OpenAI API")
        item = data_list[0]
        has_b64 = bool(item.get("b64_json"))
        url_preview = (item.get("url") or "")[:80]
        print(f"🖼️ Response format - has_b64: {has_b64}, url_preview: {url_preview}")
        return await self._save_image(item.get("b64_json"), item.get("url"))

    async def _stream_request(
        self, url: str, headers: dict, payload: dict
    ) -> tuple[str, int, int, str]:
        """Make streaming request and collect final image"""
        final_b64 = None
        final_url = None

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", url, headers=headers, json=payload
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise Exception(
                        f"OpenAI API error {resp.status_code}: {body.decode('utf-8', errors='replace')}"
                    )

                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    # Parse SSE events from buffer
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        for line in event_str.strip().split("\n"):
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    continue
                                try:
                                    event_data = json.loads(data_str)
                                    # Extract image data from event
                                    b64, url_val = self._extract_image_from_event(event_data)
                                    if b64:
                                        final_b64 = b64
                                        print(f"🖼️ Received image data (b64, length: {len(b64)})")
                                    if url_val:
                                        final_url = url_val
                                        print(f"🖼️ Received image URL")
                                except json.JSONDecodeError:
                                    pass

        # If streaming didn't yield SSE events, the response might be regular JSON
        if not final_b64 and not final_url and buffer.strip():
            try:
                result = json.loads(buffer.strip())
                data_list = result.get("data", [])
                if data_list:
                    item = data_list[0]
                    final_b64 = item.get("b64_json")
                    final_url = item.get("url")
            except json.JSONDecodeError:
                pass

        if not final_b64 and not final_url:
            raise Exception("No image data received from streaming response")

        return await self._save_image(final_b64, final_url)

    def _extract_image_from_event(self, event_data: dict) -> tuple[Optional[str], Optional[str]]:
        """Extract b64 or url image data from an SSE event"""
        b64 = None
        url_val = None

        # Handle different event structures
        data_list = event_data.get("data", [])
        if isinstance(data_list, list):
            for item in data_list:
                if isinstance(item, dict):
                    b64 = b64 or item.get("b64_json")
                    url_val = url_val or item.get("url")
        elif isinstance(data_list, dict):
            b64 = data_list.get("b64_json")
            url_val = data_list.get("url")

        # Also check top-level
        b64 = b64 or event_data.get("b64_json")
        url_val = url_val or event_data.get("url")

        return b64, url_val

    async def _save_image(
        self, b64: Optional[str], url_val: Optional[str]
    ) -> tuple[str, int, int, str]:
        """Save image from b64 or URL and return metadata"""
        image_id = generate_image_id()
        save_path = os.path.join(FILES_DIR, f'{image_id}')

        # Handle data URI in url field (e.g. "data:image/png;base64,iVBOR...")
        if not b64 and url_val and url_val.startswith("data:"):
            # Extract base64 data from data URI
            _, b64_part = url_val.split(",", 1)
            b64 = b64_part
            url_val = None

        if b64:
            mime_type, width, height, extension = await get_image_info_and_save(
                b64, save_path, is_b64=True
            )
        elif url_val:
            mime_type, width, height, extension = await get_image_info_and_save(
                url_val, save_path
            )
        else:
            raise Exception("No image data to save")

        if mime_type is None:
            raise Exception('Failed to determine image MIME type')

        filename = f'{image_id}.{extension}'
        return mime_type, width, height, filename

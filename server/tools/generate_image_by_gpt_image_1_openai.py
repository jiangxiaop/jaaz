from typing import Annotated, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool, InjectedToolCallId  # type: ignore
from langchain_core.runnables import RunnableConfig
from tools.utils.image_generation_core import generate_image_with_provider


class GenerateImageByGPTImage2InputSchema(BaseModel):
    prompt: str = Field(
        default="",
        description="Required. The prompt for image generation. If you want to edit an image, please describe what you want to edit in the prompt."
    )
    aspect_ratio: str = Field(
        default="1:1",
        description="Aspect ratio of the image, only these values are allowed: 1:1, 16:9, 4:3, 3:4, 9:16. Choose the best fitting aspect ratio according to the prompt. Best ratio for posters is 3:4. Defaults to 1:1."
    )
    input_images: Optional[list[str]] = Field(
        default=None,
        description="Optional; Image to use as reference for editing. Pass a list of image_id here, e.g. ['im_jurheut7.png']. Best for image editing cases like: Editing specific parts of the image, Removing specific objects, style transfer, etc."
    )
    tool_call_id: Annotated[str, InjectedToolCallId]


@tool("generate_image_by_gpt_image_2",
      description="Generate or edit an image using OpenAI GPT Image 2 model. Supports text-to-image generation and image editing with input reference images. High-quality image generation with excellent text rendering and photorealistic results.",
      args_schema=GenerateImageByGPTImage2InputSchema)
async def generate_image_by_gpt_image_2(
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
    prompt: str = "",
    aspect_ratio: str = "1:1",
    input_images: Optional[list[str]] = None,
) -> str:
    if not prompt or not prompt.strip():
        return "Error: prompt is required and cannot be empty. Please provide a detailed image description."

    ctx = config.get('configurable', {})
    canvas_id = ctx.get('canvas_id', '')
    session_id = ctx.get('session_id', '')

    return await generate_image_with_provider(
        canvas_id=canvas_id,
        session_id=session_id,
        provider='openai',
        model='gpt-image-2',
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        input_images=input_images,
    )


__all__ = ["generate_image_by_gpt_image_2"]

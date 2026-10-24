"""
Storage service for Fix 24/7.
FR-DIAG-01: Upload validation and limits.
- Images: <= 5 files, each <= 8MB
- Video: <= 1 file, <= 50MB
- Audio: <= 1 file, <= 10MB
Supports MinIO S3 and local storage fallback with signed/accessible URLs.
"""
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Upload Limits per FR-DIAG-01
MAX_IMAGES_COUNT = 5
MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024      # 8 MB
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024     # 50 MB
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024     # 10 MB

ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/jpg"}
ALLOWED_VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/webm",
    "audio/ogg", "audio/m4a", "audio/x-m4a", "audio/mp4"
}

MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media_uploads"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def validate_and_save_media(
        self,
        images: list[UploadFile] | None = None,
        video: UploadFile | None = None,
        audio: UploadFile | None = None,
    ) -> list[dict[str, Any]]:
        """
        Validate all files against FR-DIAG-01 size and type constraints.
        Returns list of saved media metadata dictionaries:
        [{"type": "image|video|audio", "url": str, "filename": str, "size": int}]
        """
        results: list[dict[str, Any]] = []

        # 1. Validate images
        if images:
            if len(images) > MAX_IMAGES_COUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_FILE_COUNT",
                        "message": f"Chỉ được tải lên tối đa {MAX_IMAGES_COUNT} ảnh.",
                    },
                )
            for idx, img in enumerate(images):
                content = await img.read()
                if len(content) > MAX_IMAGE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "FILE_TOO_LARGE",
                            "message": f"Ảnh số {idx + 1} vượt quá dung lượng tối đa 8MB.",
                        },
                    )
                # Check mime type
                content_type = img.content_type or "image/jpeg"
                if content_type.lower() not in ALLOWED_IMAGE_MIMES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "INVALID_FILE_TYPE",
                            "message": f"Định dạng ảnh '{content_type}' không được hỗ trợ. Vui lòng chọn JPG, PNG hoặc WEBP.",
                        },
                    )
                saved_url = await self._save_file(content, img.filename or "image.jpg", "images")
                results.append({
                    "type": "image",
                    "url": saved_url,
                    "filename": img.filename,
                    "size": len(content),
                    "content_type": content_type,
                })

        # 2. Validate video
        if video and video.filename:
            content = await video.read()
            if len(content) > MAX_VIDEO_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "FILE_TOO_LARGE",
                        "message": "Video vượt quá dung lượng tối đa 50MB.",
                    },
                )
            content_type = video.content_type or "video/mp4"
            if content_type.lower() not in ALLOWED_VIDEO_MIMES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_FILE_TYPE",
                        "message": f"Định dạng video '{content_type}' không được hỗ trợ. Vui lòng chọn MP4 hoặc WebM.",
                    },
                )
            saved_url = await self._save_file(content, video.filename or "video.mp4", "videos")
            results.append({
                "type": "video",
                "url": saved_url,
                "filename": video.filename,
                "size": len(content),
                "content_type": content_type,
            })

        # 3. Validate audio
        if audio and audio.filename:
            content = await audio.read()
            if len(content) > MAX_AUDIO_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "FILE_TOO_LARGE",
                        "message": "Bản ghi âm thanh vượt quá dung lượng tối đa 10MB.",
                    },
                )
            content_type = audio.content_type or "audio/webm"
            # Flexible audio mime check
            if not any(m in content_type.lower() for m in ("audio", "webm", "ogg", "mp3", "wav", "m4a")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_FILE_TYPE",
                        "message": f"Định dạng âm thanh '{content_type}' không được hỗ trợ.",
                    },
                )
            saved_url = await self._save_file(content, audio.filename or "audio.webm", "audios")
            results.append({
                "type": "audio",
                "url": saved_url,
                "filename": audio.filename,
                "size": len(content),
                "content_type": content_type,
            })

        return results

    async def _save_file(self, content: bytes, original_name: str, folder: str) -> str:
        """Save file bytes to media folder and return accessible URL."""
        ext = os.path.splitext(original_name)[1] or ".bin"
        filename = f"{secrets.token_hex(16)}{ext}"
        target_dir = MEDIA_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        return f"/media/{folder}/{filename}"


_storage_instance = StorageService()


def get_storage_service() -> StorageService:
    return _storage_instance

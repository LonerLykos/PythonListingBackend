import uuid
import io
from pathlib import Path
from fastapi import UploadFile
from PIL import Image
from app.core.config import settings


class Storage:
    def __init__(self, media_root: str = settings.media_root):
        self.media_root = Path(media_root)
        self.media_root.mkdir(parents=True, exist_ok=True)

    async def save_images(self, listing_id: int, files: list[UploadFile]) -> list[str]:
        listing_dir = self.media_root / f"listings/{listing_id}"
        listing_dir.mkdir(parents=True, exist_ok=True)
        urls = []

        for file in files:
            contents = await file.read()

            image = Image.open(io.BytesIO(contents)).convert("RGB")

            image.thumbnail((1024, 720), Image.Resampling.LANCZOS)

            extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'jpg'
            if extension not in ['jpg', 'jpeg', 'png']:
                extension = 'jpg'

            filename = f"{uuid.uuid4()}.{extension}"
            file_path = listing_dir / filename

            with file_path.open("wb") as f:
                image.save(
                    f,
                    format='JPEG' if extension in ['jpg', 'jpeg'] else 'PNG',
                    optimize=True,
                    quality=85
                )

            url = f"{settings.media_url.rstrip('/')}/listings/{listing_id}/{filename}"
            urls.append(url)

        return urls

    def delete_images(self, urls: list[str]) -> None:
        for url in urls:
            relative_path = url.replace(settings.media_url, "")
            file_path = self.media_root / relative_path.lstrip("/")
            if file_path.exists():
                file_path.unlink()


storage = Storage()

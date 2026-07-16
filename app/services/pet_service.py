import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.pet import Pet
from app.repositories.pet_repo import PetRepository
from app.schemas.pet import PetCreate, PetUpdate

UPLOADS_DIR = Path("app/static/uploads")
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class PetService:
    def __init__(self, db: AsyncSession):
        self.repo = PetRepository(db)

    async def get_pets(self, owner_id: int) -> list[Pet]:
        return await self.repo.get_all_by_owner(owner_id)

    async def get_pet(self, pet_id: int, owner_id: int) -> Pet:
        pet = await self.repo.get_by_id(pet_id)
        if not pet:
            raise NotFoundError("Pet not found")
        if pet.owner_id != owner_id:
            raise ForbiddenError("Not your pet")
        return pet

    async def create_pet(self, owner_id: int, data: PetCreate) -> Pet:
        return await self.repo.create(owner_id, data)

    async def update_pet(self, pet_id: int, owner_id: int, data: PetUpdate) -> Pet:
        pet = await self.get_pet(pet_id, owner_id)
        return await self.repo.update(pet, data)

    async def upload_avatar(self, pet_id: int, owner_id: int, file: UploadFile) -> Pet:
        pet = await self.get_pet(pet_id, owner_id)

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise BadRequestError("Допустимы только изображения: JPEG, PNG, WebP, GIF")

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        ext = (file.filename or "photo").rsplit(".", 1)[-1].lower()
        filename = f"pet_{pet_id}_{uuid.uuid4().hex[:10]}.{ext}"

        if pet.avatar_path:
            old = Path("app/static") / pet.avatar_path.removeprefix("/static/")
            if old.exists():
                old.unlink()

        content = await file.read()
        (UPLOADS_DIR / filename).write_bytes(content)

        return await self.repo.update_avatar(pet, f"/static/uploads/{filename}")

    async def delete_pet(self, pet_id: int, owner_id: int) -> None:
        pet = await self.get_pet(pet_id, owner_id)
        if pet.avatar_path:
            old = Path("app/static") / pet.avatar_path.removeprefix("/static/")
            if old.exists():
                old.unlink()
        await self.repo.delete(pet)

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.pet import Pet
from app.models.user import User
from app.schemas.pet import PetCreate, PetResponse, PetUpdate
from app.schemas.pet_report import PetReportRequest
from app.services.pet_report_service import PetReportService
from app.services.pet_service import PetService

router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("", response_model=list[PetResponse])
async def list_pets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Pet]:
    return await PetService(db).get_pets(current_user.id)


@router.post("", response_model=PetResponse, status_code=201)
async def create_pet(
    data: PetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pet:
    return await PetService(db).create_pet(current_user.id, data)


@router.get("/{pet_id}", response_model=PetResponse)
async def get_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pet:
    return await PetService(db).get_pet(pet_id, current_user.id)


@router.patch("/{pet_id}", response_model=PetResponse)
async def update_pet(
    pet_id: int,
    data: PetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pet:
    return await PetService(db).update_pet(pet_id, current_user.id, data)


@router.post("/{pet_id}/avatar", response_model=PetResponse)
async def upload_avatar(
    pet_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Pet:
    return await PetService(db).upload_avatar(pet_id, current_user.id, file)


@router.delete("/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await PetService(db).delete_pet(pet_id, current_user.id)


@router.post(
    "/{pet_id}/report",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "PDF-карточка питомца"}},
)
async def download_pet_report(
    pet_id: int,
    data: PetReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pet, pdf = await PetReportService(db).build_pdf(pet_id, current_user.id, data)
    filename = f"Карточка_{pet.name}_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        # filename* carries the Cyrillic name; the plain one is an ASCII fallback.
        headers={
            "Content-Disposition": f"attachment; filename=\"pet_card_{pet_id}.pdf\"; "
            f"filename*=UTF-8''{quote(filename)}"
        },
    )

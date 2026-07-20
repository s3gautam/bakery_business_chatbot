from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import MenuItemOut

router = APIRouter()


@router.get("/menu", response_model=list[MenuItemOut])
async def get_menu(session: AsyncSession = Depends(get_session)) -> list[MenuItemOut]:
    repository = MenuRepository(session)
    items = await repository.list_available()
    return [MenuItemOut.model_validate(item) for item in items]

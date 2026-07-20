from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.config_repository import ConfigRepository
from app.schemas.config import BusinessConfigOut, BusinessConfigUpdate

router = APIRouter()


@router.get("/config", response_model=BusinessConfigOut)
async def get_config(session: AsyncSession = Depends(get_session)) -> BusinessConfigOut:
    repository = ConfigRepository(session)
    config = await repository.get()
    await session.commit()
    return BusinessConfigOut.model_validate(config)


@router.put("/config", response_model=BusinessConfigOut)
async def update_config(
    payload: BusinessConfigUpdate, session: AsyncSession = Depends(get_session)
) -> BusinessConfigOut:
    repository = ConfigRepository(session)
    fields = payload.model_dump(exclude_unset=True)
    if "menu_source_url" in fields and fields["menu_source_url"] is not None:
        fields["menu_source_url"] = str(fields["menu_source_url"])
    config = await repository.update(**fields)
    await session.commit()
    return BusinessConfigOut.model_validate(config)

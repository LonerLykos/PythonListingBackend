from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy import select
from app.schemas.profanity_word import (
    ProfanityWordsBase,
    ProfanityWords as ProfanityWordsResponse
)
from app.schemas.listing import MessageResponse
from app.models.user import User
from app.models.profanity_words import ProfanityWords as ProfanityWordsModel
from app.db.database import get_listing_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions_checker import permission_checker
from app.utils.token_utils import get_user_from_token

router = APIRouter(prefix="/profanity", tags=["profanity"])


@router.get('', response_model=list[ProfanityWordsResponse], status_code=status.HTTP_200_OK)
async def get_profanity_words(
        user:User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_profanity_words')
    result = await db.execute(select(ProfanityWordsModel))
    return result.scalars().all()


@router.post('', response_model=ProfanityWordsResponse, status_code=status.HTTP_201_CREATED)
async def create_profanity_word(
        word: ProfanityWordsBase,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_profanity_words')
    db_profanity_word = ProfanityWordsModel(word=word.word)
    db.add(db_profanity_word)
    await db.commit()
    await db.refresh(db_profanity_word)
    return db_profanity_word


@router.delete('/{profanity_id}', response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_profanity_word(
        profanity_id: int,
        user: User = Depends(get_user_from_token),
        db: AsyncSession = Depends(get_listing_db)):
    await permission_checker(user, 'manage_profanity_words')
    db_profanity_word = await db.get(ProfanityWordsModel, profanity_id)
    if not db_profanity_word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Profanity word not found')
    await db.delete(db_profanity_word)
    await db.commit()
    return MessageResponse(message=f'Profanity_word {profanity_id} deleted')

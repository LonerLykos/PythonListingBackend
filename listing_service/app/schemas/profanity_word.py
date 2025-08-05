from pydantic import BaseModel, ConfigDict


class ProfanityWordsBase(BaseModel):
    word: str


class ProfanityWords(ProfanityWordsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

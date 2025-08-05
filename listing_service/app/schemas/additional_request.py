from typing import Literal
from pydantic import BaseModel


class AddCountry(BaseModel):
    type: Literal['add_country']
    name: str


class AddRegion(BaseModel):
    type: Literal['add_region']
    name: str
    country_name: str


class AddCity(BaseModel):
    type: Literal['add_city']
    name: str
    region_name: str
    country_name: str


class AddBrand(BaseModel):
    type: Literal['add_brand']
    name: str


class AddCarModel(BaseModel):
    type: Literal['add_carmodel']
    name: str
    brand_name: str


AddEntityRequest = AddCountry | AddRegion | AddCity | AddBrand | AddCarModel

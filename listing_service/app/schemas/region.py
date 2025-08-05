from pydantic import BaseModel, field_serializer, ConfigDict


class CountryBase(BaseModel):
    name: str


class Country(CountryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CountryWithRegions(Country):
    id: int
    regions: list['Region'] = []

    @field_serializer("regions")
    def serialize_regions(self, regions: list):
        return [RegionInCountry.model_validate(r) for r in regions]

    model_config = ConfigDict(from_attributes=True)


class RegionBase(BaseModel):
    country_id: int
    name: str


class RegionInCountry(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class Region(RegionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RegionWithCities(Region):
    cities: list["City"] = []

    @field_serializer('cities')
    def serialize_cities(self, cities: list):
        return [CitiesInRegion.model_validate(c) for c in cities]

    model_config = ConfigDict(from_attributes=True)


class CityBase(BaseModel):
    region_id: int
    name: str


class CitiesInRegion(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class City(CityBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

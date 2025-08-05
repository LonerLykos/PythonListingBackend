from pydantic import BaseModel, field_serializer, ConfigDict


class BrandBase(BaseModel):
    name: str


class Brand(BrandBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BrandWithModels(Brand):
    car_models: list["CarModelInBrand"] = []

    @field_serializer("car_models")
    def serialize_models(self, car_models: list):
        return [CarModelInBrand.model_validate(m) for m in car_models]

    model_config = ConfigDict(from_attributes=True)


class CarModelBase(BaseModel):
    brand_id: int
    name: str


class CarModelInBrand(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CarModel(CarModelBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

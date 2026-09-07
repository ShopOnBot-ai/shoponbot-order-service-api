from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AddressBase(BaseModel):
    name: str
    phone: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Decimal
    longitude: Decimal


class AddressRequest(AddressBase):
    pass


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    id: int
    user_id: int
    address: AddressBase


class AddressDBResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    phone: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Decimal
    longitude: Decimal


class AddressesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    user_id: int
    addresses: list[AddressDBResponse]

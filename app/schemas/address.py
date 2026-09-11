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


class AddressUpdate(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class AddressUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    address_id: int


class AddressDeleteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    address_id: int

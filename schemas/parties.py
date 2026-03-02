from pydantic import BaseModel, Field


class Representative(BaseModel):
    """
    A representative of a party member.
    """

    name: str = Field(description="The name of the representative.")
    title: str = Field(description="The title of the representative.")
    email: str = Field(description="The email of the representative.")


class PartyMember(BaseModel):
    """
    A member of a party involved in a contract.
    """

    company_name: str = Field(description="The name of the company.")
    address: str = Field(description="The address of the company.")
    representative: Representative = Field(
        description="The representative of the company."
    )


class Parties(BaseModel):
    provider: PartyMember = Field(description="The provider of the contract.")
    customer: PartyMember = Field(description="The customer of the contract.")

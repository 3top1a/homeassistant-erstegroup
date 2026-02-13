from dataclasses import dataclass
from typing import Any


@dataclass
class Account:
    id: str # Internal API identifier
    currency: str # Three digit ISO identifier
    nameI18N: str # Owner name
    productI18N: str # Account name
    identification: dict[str, str] # e.g., 'iban': 'CZ...'

    servicer: dict[str, str]
    ownersNames: list[str]
    relationship: dict[str, Any]
    suitableScope: dict[str, str]

    def get_iban(self) -> str | None:
        return self.identification.get("iban")

    # I don't know *why*, but a previous version did None checks
    # for name and product, so that's why this is here
    def get_name(self) -> str:
        return self.nameI18N

    def get_product(self) -> str:
        return self.productI18N

@dataclass
class Balance:
    amount: float
    currency: str


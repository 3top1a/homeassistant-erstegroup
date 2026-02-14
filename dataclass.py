from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

type Balance = MonetaryAmount


@dataclass
class Account:
    id: str  # Internal API identifier
    currency: str  # ISO 4217, only really denotes the currency of the country where the user has registered.
    name: str  # Owner name
    product: str  # Account name
    iban: str


def account_from_api(data: dict[str, Any]) -> Account:
    return Account(
        id=data["id"],
        currency=data["currency"],
        name=data["name118N"],
        product=data["productI18N"],
        iban=data["identification"]["iban"],
    )


@dataclass
class MonetaryAmount:
    amount: float
    currency: str  # ISO 4217


class DebitCreditEnum(Enum):
    Credit = "CRDT"  # Credit transaction
    Debit = "DBIT"  # Debit transaction


class TransactionStatusEnum(Enum):
    Info = "INFO"  # Transactions that do not affect the account balance such as bank informative transactions,
    # e.g. change of interest rate, and failed transactions.
    Book = "BOOK"  # Settled entry


@dataclass
class PaymentActor:
    name: str
    iban: str


@dataclass
class Transaction:
    entryReference: str  # Internal ref, e.g., `FC-4567513951`
    amount: MonetaryAmount
    creditDebitIndicator: DebitCreditEnum
    status: TransactionStatusEnum
    bookingDate: date
    valueDate: date

    creditor: PaymentActor
    debitor: PaymentActor


def transaction_from_api(transaction: dict[str, Any]) -> Transaction:
    relatedParties = transaction["entryDetails"]["transactionDetails"]["relatedParties"]
    creditor_name = relatedParties["creditor"]["name"]
    debitor_name = relatedParties["debitor"]["name"]
    creditor_iban = relatedParties["creditorAccount"]["identification"]["iban"]
    debitor_iban = relatedParties["debitorAccount"]["identification"]["iban"]

    return Transaction(
        entryReference=transaction["entryReference"],
        amount=MonetaryAmount(
            amount=float(transaction["amount"]["value"]),
            currency=transaction["amount"]["currency"],
        ),
        creditDebitIndicator=DebitCreditEnum(transaction["creditDebitIndicator"]),
        status=TransactionStatusEnum(transaction["status"]),
        bookingDate=_parse_date(transaction["bookingDate"]),
        valueDate=_parse_date(transaction["valueDate"]),
        creditor=PaymentActor(name=creditor_name, iban=creditor_iban),
        debitor=PaymentActor(name=debitor_name, iban=debitor_iban),
    )


def _parse_date(inp: str) -> date:
    return date.fromisoformat(inp)

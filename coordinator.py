"""Data update coordinator for ErsteGroup."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_ACCOUNTS,
    API_BALANCES,
    API_TRANSACTIONS,
    CONF_API_BASE_URL,
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_IDP_BASE_URL,
    CONF_REFRESH_TOKEN,
    UPDATE_INTERVAL,
)
from .dataclass import (
    Account,
    Balance,
    DebitCreditEnum,
    MonetaryAmount,
    Transaction,
    account_from_api,
    transaction_from_api,
)

_LOGGER = logging.getLogger(__name__)


class ErsteGroupCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        # TODO Move runtime data to ConfigEntry.runtime_data
        self.entry = entry
        self.api_key: str = entry.data[CONF_API_KEY]
        self.api_base_url: str = entry.data[CONF_API_BASE_URL].rstrip("/")
        self.idp_base_url: str = entry.data[CONF_IDP_BASE_URL].rstrip("/")
        self.client_id = entry.data[CONF_CLIENT_ID]
        self.client_secret = entry.data[CONF_CLIENT_SECRET]
        self.refresh_token = entry.data[CONF_REFRESH_TOKEN]
        self.access_token = None
        self.session = async_get_clientsession(hass)
        self.accounts: list[Account] | None = None

        super().__init__(
            hass,
            _LOGGER,
            name="ErsteGroup",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            config_entry=entry,
        )

    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        # TODO More intelligent token handling
        # Maybe natively through home assistant?

        url = f"{self.idp_base_url}/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        # TODO This exception handling is a mess, refactor
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 401:
                    raise ConfigEntryAuthFailed("Refresh token expired")

                response.raise_for_status()
                token_data = await response.json()
                self.access_token = token_data["access_token"]

                if "refresh_token" in token_data:
                    self.refresh_token = token_data["refresh_token"]
                    _LOGGER.info("New refresh token received")

                return self.access_token
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            # TODO Does this maybe leak secrets?
            _LOGGER.error(
                "Failed to refresh access token: %s, %s", response.json(), err
            )
            raise UpdateFailed(
                f"Authentication failed: {response.json()}, {err}"
            ) from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Entry point from hass"""
        self.access_token = await self._get_access_token()

        self.accounts = await self._fetch_accounts()

        # TODO Convert `data` this to a dataclass
        data = {"accounts": {}}
        for account in self.accounts:
            # Fetch balance
            balance = await self._fetch_balance(account.id)

            # TODO This could just be one fetch transactions and then would just get filtered
            # Fetch transactions for current month to date (1st to current day)
            transactions_month = await self._fetch_transactions(account.id, days=None)
            spending_month, income_month = self._calculate_spending_income(
                transactions_month
            )

            # Fetch transactions for last 30 days
            transactions_30d = await self._fetch_transactions(account.id, days=30)
            spending_30d, income_30d = self._calculate_spending_income(transactions_30d)

            # TODO This could be moved elsewhere
            data["accounts"][account.id] = {
                "id": account.id,
                "number": account.iban,
                "name": account.name,
                "friendly_name": account.name + " " + account.product,
                "product": account.product,
                "currency": balance.currency,
                "balance": balance.amount,
                "spending_mtd": spending_month,
                "income_mtd": income_month,
                "spending_30d": spending_30d,
                "income_30d": income_30d,
            }

        return data

    async def _fetch_accounts(self) -> list[Account]:
        """Fetch accounts list"""
        # See https://developers.erstegroup.com/docs/apis/bank.csas/bank.csas.v1%2Fpayments for API docs
        url = f"{self.api_base_url}{API_ACCOUNTS}"
        headers = self._construct_auth_headers()

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            accounts = data.get("accounts", [])
            return [account_from_api(account) for account in accounts]

    async def _fetch_balance(self, account_id: str) -> Balance:
        """Fetch current balance of an account"""
        url = f"{self.api_base_url}{API_BALANCES.format(account_id=account_id)}"
        headers = self._construct_auth_headers()

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

            assert len(data["balances"]) > 0, (
                f"Expected more than zero balances on account {account_id}"
            )

            balance_data = data["balances"][0]
            amount = float(balance_data["amount"]["value"])
            currency = balance_data["amount"]["currency"]

            return MonetaryAmount(amount, currency)

    async def _fetch_transactions(
        self, account_id: str, days: int | None = None
    ) -> list[Transaction]:
        """Fetch transactions for an account"""
        # See https://developers.erstegroup.com/docs/apis/bank.csas/bank.csas.v3%2Faccounts for API docs
        today = datetime.now()

        if days is None:
            # Current month
            from_date = today.replace(day=1).strftime("%Y-%m-%d")
        else:
            # Last N days
            from_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")

        url = f"{self.api_base_url}{API_TRANSACTIONS.format(account_id=account_id)}"
        params = {"fromDate": from_date, "size": 100}
        headers = self._construct_auth_headers()

        async with self.session.get(url, headers=headers, params=params) as response:
            # TODO This api is paged, implement paging when needed
            response.raise_for_status()
            data = await response.json()

            return [
                transaction_from_api(transaction)
                for transaction in data["transactions"]
            ]

    def _construct_auth_headers(self) -> dict[str, str]:
        headers = {
            "WEB-API-key": self.api_key,
            "Authorization": f"Bearer {self.access_token}",
        }
        return headers

    def _calculate_spending_income(
        self, transactions: list[Transaction]
    ) -> tuple[float, float]:
        """Calculate spending and income excluding internal transfers."""
        # TODO Move to different file
        spending = 0.0
        income = 0.0
        # Requires self.accounts to be set before calling
        own_ibans = (
            [account.iban for account in self.accounts] if self.accounts else []
        )

        for transaction in transactions:
            credit_debit = transaction.creditDebitIndicator
            amount = transaction.amount.amount

            if credit_debit == DebitCreditEnum.Debit:
                # Outgoing transaction - check if it's internal
                if transaction.creditor.iban in own_ibans:
                    continue

                spending += amount

            elif credit_debit == DebitCreditEnum.Credit:
                # Incoming transaction - check if it's internal
                if transaction.debitor.iban in own_ibans:
                    continue

                income += amount

        return spending, income

"""Data update coordinator for ErsteGroup."""
from __future__ import annotations

import logging
from datetime import timedelta, datetime
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
    UPDATE_INTERVAL,
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_API_BASE_URL,
    CONF_IDP_BASE_URL,
    CONF_PAYDAY,
)

_LOGGER = logging.getLogger(__name__)


class ErsteGroupCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ErsteGroup data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.api_key = entry.data[CONF_API_KEY]
        self.api_base_url = entry.data[CONF_API_BASE_URL].rstrip("/")
        self.idp_base_url = entry.data[CONF_IDP_BASE_URL].rstrip("/")
        self.client_id = entry.data[CONF_CLIENT_ID]
        self.client_secret = entry.data[CONF_CLIENT_SECRET]
        self.refresh_token = entry.data[CONF_REFRESH_TOKEN]
        self.payday = entry.data[CONF_PAYDAY]
        self.access_token = None
        self.session = async_get_clientsession(hass)
        self.account_numbers = {}

        super().__init__(
            hass,
            _LOGGER,
            name="ErsteGroup",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            config_entry=entry,
        )

    def _calculate_days_until_payday(self) -> int:
        """Calculate days until next payday."""
        today = datetime.now()
        current_day = today.day

        if current_day < self.payday:
            # Payday is this month
            payday_date = today.replace(day=self.payday)
        else:
            # Payday is next month
            if today.month == 12:
                payday_date = today.replace(year=today.year + 1, month=1, day=self.payday)
            else:
                # Handle months with fewer days (e.g., payday=31 but next month is Feb)
                next_month = today.month + 1
                year = today.year

                # Try to set the payday, if it fails (e.g., Feb 31), use last day of month
                try:
                    payday_date = today.replace(month=next_month, day=self.payday)
                except ValueError:
                    # Payday doesn't exist in next month, use last day
                    if next_month == 12:
                        payday_date = today.replace(month=12, day=31)
                    else:
                        payday_date = today.replace(month=next_month + 1, day=1) - timedelta(days=1)

        days_until = (payday_date - today).days
        return days_until

    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self.access_token:
            return self.access_token

        url = f"{self.idp_base_url}/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

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
            _LOGGER.error("Failed to refresh access token: %s, %s", response.json(), err)
            raise UpdateFailed(f"Authentication failed: {response.json()}, {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            self.access_token = None
            access_token = await self._get_access_token()

            accounts = await self._fetch_accounts(access_token)
            data = {"accounts": {}}

            for account in accounts:
                account_id = account["id"]
                account_number = account.get("identification", {}).get("iban", "")

                self.account_numbers[account_number] = account_id

                # Fetch balance
                balance = await self._fetch_balance(account_id, access_token)

                # Fetch transactions for current month (for monthly spending)
                transactions_month = await self._fetch_transactions(
                    account_id, access_token, days=None
                )
                spending_month = self._calculate_spending(transactions_month, account_number)

                # Fetch transactions for last 30 days (for ratio calculation)
                transactions_30d = await self._fetch_transactions(
                    account_id, access_token, days=30
                )
                spending_30d, income_30d = self._calculate_spending_income(
                    transactions_30d, account_number
                )

                # Calculate metrics
                ratio = (spending_30d / income_30d * 100) if income_30d > 0 else 0
                daily_burn = spending_30d / 30
                days_until_payday = self._calculate_days_until_payday()

                # Calculate runway (days until money runs out at current burn rate)
                runway_days = balance["amount"] / daily_burn if daily_burn > 0 else 999

                # Calculate financial health score
                if days_until_payday <= 1:
                    days_until_payday = 2

                safety_margin = runway_days / days_until_payday

                # Determine status
                if safety_margin >= 2.0:
                    status = "excellent"
                    emoji = "💰"
                    message = "Go treat yourself!"
                elif safety_margin >= 1.5:
                    status = "good"
                    emoji = "✅"
                    message = "You're doing fine"
                elif safety_margin >= 1.0:
                    status = "ok"
                    emoji = "⚠️"
                    message = "Be careful with spending"
                elif safety_margin >= 0.7:
                    status = "warning"
                    emoji = "🔶"
                    message = "Time to cut back"
                else:
                    status = "danger"
                    emoji = "🚨"
                    message = "Oh fuck oh shit"

                data["accounts"][account_id] = {
                    "id": account_id,
                    "name": account.get("nameI18N", "Unknown Account"),
                    "friendly_name": account.get("nameI18N", "Unknown Account") + " " + account.get("productI18N",
                                                                                                      "Unknown product"),
                    "number": account_number,
                    "currency": account.get("currency", "CZK"),
                    "balance": balance,
                    "spending": spending_month,
                    "spending_30d": spending_30d,
                    "income_30d": income_30d,
                    "spending_ratio": ratio,
                    "daily_burn": daily_burn,
                    "runway_days": runway_days,
                    "days_until_payday": days_until_payday,
                    "safety_margin": safety_margin,
                    "financial_health_status": status,
                    "financial_health_emoji": emoji,
                    "financial_health_message": message,
                    "product": account.get("productI18N", "Unknown product"),
                }

            return data

        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_accounts(self, access_token: str) -> list:
        """Fetch accounts list."""
        url = f"{self.api_base_url}{API_ACCOUNTS}"
        headers = {
            "WEB-API-key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("accounts", [])

    async def _fetch_balance(self, account_id: str, access_token: str) -> dict:
        """Fetch account balance."""
        url = f"{self.api_base_url}{API_BALANCES.format(account_id=account_id)}"
        headers = {
            "WEB-API-key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

            for balance in data.get("balances", []):
                # balance_type = balance.get("type", {})
                # code = balance_type.get("codeOrProprietary", {}).get("code")
                # There was a DBIT check here, but that's useless (I think)
                return {
                    "amount": float(balance["amount"]["value"]),
                    "currency": balance["amount"]["currency"],
                }

            _LOGGER.error("Error fetching account balance: %s", data)
            return {"amount": -123.0, "currency": "EBALANCE"}

    async def _fetch_transactions(
            self, account_id: str, access_token: str, days: int | None = None
    ) -> list:
        """Fetch account transactions.

        Args:
            account_id: The account ID
            access_token: OAuth access token
            days: Number of days to fetch (None = current month)
        """
        today = datetime.now()

        if days is None:
            # Current month
            from_date = today.replace(day=1).strftime("%Y-%m-%d")
        else:
            # Last N days
            from_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")

        url = f"{self.api_base_url}{API_TRANSACTIONS.format(account_id=account_id)}"
        params = {"fromDate": from_date, "size": 100}
        headers = {
            "WEB-API-key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("transactions", [])

    def _calculate_spending(self, transactions: list, account_number: str) -> float:
        """Calculate spending excluding internal transfers."""
        spending = 0.0

        for transaction in transactions:
            if transaction.get("creditDebitIndicator") != "DBIT":
                continue

            entry_details = transaction.get("entryDetails", {})
            transaction_details = entry_details.get("transactionDetails", {})
            related_parties = transaction_details.get("relatedParties", {})

            creditor = related_parties.get("creditor", {})
            creditor_account = creditor.get("account", {})
            creditor_iban = creditor_account.get("identification", {}).get("iban", "")

            if creditor_iban in self.account_numbers:
                continue

            amount = float(transaction.get("amount", {}).get("value", 0))
            spending += amount

        return spending

    def _calculate_spending_income(
            self, transactions: list, account_number: str
    ) -> tuple[float, float]:
        """Calculate spending and income excluding internal transfers.

        Returns:
            Tuple of (spending, income)
        """
        spending = 0.0
        income = 0.0

        for transaction in transactions:
            credit_debit = transaction.get("creditDebitIndicator")
            entry_details = transaction.get("entryDetails", {})
            transaction_details = entry_details.get("transactionDetails", {})
            related_parties = transaction_details.get("relatedParties", {})
            amount = float(transaction.get("amount", {}).get("value", 0))

            if credit_debit == "DBIT":
                # Outgoing transaction - check if it's internal
                creditor = related_parties.get("creditorAccount", {})
                creditor_iban = creditor.get("identification", {}).get("iban", "")

                if creditor_iban not in self.account_numbers:
                    spending += amount

            elif credit_debit == "CRDT":
                # Incoming transaction - check if it's internal
                debtor = related_parties.get("debtorAccount", {})
                debtor_iban = debtor.get("identification", {}).get("iban", "")

                if debtor_iban not in self.account_numbers:
                    income += amount

        return spending, income

# Home Assistant ErsteGroup Integration

![Image showing the integration in Home Assistant](image.png)

Custom integration for Home Assistant to track ErsteGroup (specifically developed for Česká Spořitelna, probably works
for others) banking accounts.

## Features

- Balance tracking
- Monthly spending calculation
- Spending/income ratio
- Financial health indicator (runway until payday)

## Getting the API keys

Go to the [ErsteGroup developer portal](https://developers.erstegroup.com/), create a new organization (without a DIC),
and a new project. Use OAuth2 (**set your redirect url to `https://example.com`, and 180 days until expiry**) and enable
the `Premium - Accounts API (v3)` API (free for natural persons' accounts,
otherwise
300CZK/month).

Once you have filled out everything in your HA configuration except the refresh token, you can click on the 'ErsteGroup
Re-authenticate' button in HA to get your refresh token.

If everything works correctly, apply for production access. For me this took about four business days.

## Installation

### HACS

1. Add this repository as a custom repository in HACS
2. Install "ErsteGroup Banking"
3. Restart Home Assistant

### Manual

1. Make a `custom_components` directory in your HA config directory
2. Run `git clone https://github.com/3top1a/homeassistant-erstegroup.git`
3. Restart Home Assistant

## Configuration

Add to your `configuration.yaml`:

```yaml
erstegroup:
  api_key: "YOUR_API_KEY"
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  refresh_token: "YOUR_REFRESH_TOKEN" # Your refresh token, does not support automatic authentication yet
  # Api and Idp urls from your develop config portal
  api_base_url: "https://webapi.developers.erstegroup.com/api/csas/public/sandbox/v3/accounts" # defaults to sandbox, use `https://www.csas.cz/webapi/api/v3/accounts` for prod
  idp_base_url: "https://webapi.developers.erstegroup.com/api/csas/sandbox/v1/sandbox-idp" # defaults to sandbox, use `https://bezpecnost.csas.cz/api/psd2/fl/oidc/v1` for prod
  payday: 1  # optional, Day of month when you get paid (1-31). Default: 1
```

## Sensors

- `sensor.{account}_balance` - Current account balance
- `sensor.{account}_monthly_spending` - Current month spending (excluding internal transfers between accounts)
- `sensor.{account}_spending_ratio` - Last 30 days spending/income ratio
- `sensor.{account}_financial_health` - Safety margin, calculated as
  `days until money runs out at current burn rate / days until payday`

## License

MIT

# Home Assistant ErsteGroup Integration

Custom integration for Home Assistant to track ErsteGroup (specifically developed for Česká Spořitelna) banking accounts.

## Features

- Balance tracking
- Monthly spending calculation
- Spending/income ratio
- Financial health indicator (runway until payday)

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Install "ErsteGroup Banking"
3. Restart Home Assistant

### Manual

1. Copy the `custom_components/erstegroup` directory to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

Add to your `configuration.yaml`:

```yaml
erstegroup:
  api_key: "YOUR_API_KEY"
  client_id: "YOUR_CLIENT_ID"
  client_secret: "YOUR_CLIENT_SECRET"
  refresh_token: "YOUR_REFRESH_TOKEN"
  payday: 1  # Day of month when you get paid (1-31)
```

## Sensors

- `sensor.{account}_balance` - Current account balance
- `sensor.{account}_monthly_spending` - Current month spending (excluding internal transfers)
- `sensor.{account}_spending_ratio` - Last 30 days spending/income ratio
- `sensor.{account}_financial_health` - Safety margin until payday

## License

MIT

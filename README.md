# PowerRates - Tesla Powerwall Dynamic Pricing

A Python script that automatically updates Tesla Powerwall electricity rates based on ENTSOE day-ahead market prices.

## Features

- Fetches real-time electricity prices from ENTSOE transparency platform
- Automatically configures Tesla Powerwall Time-of-Use (TOU) rates
- Supports dynamic rate bands based on market price percentiles
- Includes fallback to stub implementation for testing
- Secure API key management with local JSON files

## Prerequisites

- Python 3.8+
- Tesla Powerwall with Time-of-Use enabled
- ENTSOE API key (register at <https://transparency.entsoe.eu/>)
- Tesla account with API access

## Installation

1. Clone or download the project files
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure API keys:
   - Edit `entsoe_api_key.json` with your ENTSOE API key
   - The Tesla refresh token will be automatically managed

## Configuration

### ENTSOE API Key

Edit `entsoe_api_key.json`:

```json
{"api_key": "your_entsoe_api_key_here"}
```

### Environment Variables (Optional)

- `TESLA_USE_SIMPLIFIED_TOU=true` - Use simplified 2-period TOU format
- `TESLA_APPLY_TODAY_RATES=true` - Apply today's rates (for early execution)
- `DEBUG=true` - Enable debug output

## Usage

### Basic Execution

```bash
python powerrates.py
```

### VS Code Debugging

Use the pre-configured launch configurations:

- `Run PowerRates Main Script` - Execute the main script
- `Debug PowerRates Main Script` - Debug with breakpoints
- `Run PowerRates Tests` - Run the test suite
- `Debug PowerRates Tests` - Debug specific tests

### Testing

```bash
python -m unittest test_powerrates -v
```

### API Connectivity Testing

The test suite includes an integration test that validates actual connectivity to the ENTSOE API:

```bash
# Run only the connectivity test
python -m unittest test_powerrates.TestEntsoeApiKey.test_entsoe_api_connectivity_with_real_key -v
```

This test will:

- ✅ Verify your API key is properly formatted
- ✅ Test actual network connectivity to ENTSOE
- ✅ Validate API response structure
- ✅ Skip automatically if using placeholder credentials

## Project Structure

```
/Users/ries/oteny/power/
├── powerrates.py           # Main script
├── test_powerrates.py      # Test suite
├── entsoe_api_key.json     # ENTSOE API key (configure this)
├── tesla_refresh_token.json# Tesla refresh token (auto-managed)
├── requirements.txt        # Python dependencies
├── .vscode/                # VS Code configuration
│   ├── launch.json        # Debug configurations
│   ├── tasks.json         # Build tasks
│   └── settings.json      # Editor settings
├── .gitignore             # Git ignore patterns
└── README.md              # This file
```

## Testing

The project includes comprehensive unit tests following Python best practices:

- `test_powerrates.py` - Complete test suite using unittest
- Tests for API key loading, price fetching, and utility functions
- Mocked external API calls for reliable testing
- Edge case and error handling coverage

Run tests:

```bash
# From VS Code: Use "Run PowerRates Tests" launch config
# Or from terminal:
python3 -m unittest test_powerrates -v
```

## Development

### VS Code Setup

The project includes optimized VS Code configuration:

- Pre-configured debug launchers for main script and tests
- Python linting with flake8
- Code formatting with black
- Integrated terminal tasks

### Code Quality

- Follows PEP 8 style guidelines
- Line length limit: 120 characters
- Comprehensive test coverage
- Type hints where appropriate

## Security Notes

- API keys are stored in local JSON files (excluded from git)
- Tesla refresh tokens are automatically managed
- Never commit sensitive credentials to version control

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure `entsoe_api_key.json` contains a valid ENTSOE API key
2. **Tesla Authentication**: First run may require browser authentication
3. **Network Issues**: Check internet connectivity for API calls
4. **SSL Certificate Issues** (macOS): If you encounter SSL certificate errors:

   ```bash
   # Run the certificate installer (recommended)
   /Applications/Python\ 3.12/Install\ Certificates.command

   # Or update certifi package
   pip install --upgrade certifi
   ```

### Debug Mode

Enable debug output:

```bash
DEBUG=true python3 powerrates.py
```

### Test Debugging

Use VS Code's "Debug PowerRates Tests" configuration to step through test execution.

## Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

This project is provided as-is for educational and personal use.

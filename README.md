# CME Gold Volume Scraper

A Flask web application that scrapes CME Gold trading volume data and serves it via REST API.

## Features

- 🐍 **Python Flask** - Clean, modern web framework
- 🕷️ **Web Scraping** - Extracts CME Gold volume data using requests + BeautifulSoup
- 🌐 **REST API** - JSON and HTML response formats
- 📊 **Date Filtering** - Optional trade date parameter for historical data
- 🏥 **Health Checks** - Built-in monitoring endpoints
- 🚀 **cPanel Ready** - Optimized for shared hosting deployment

## API Endpoints

| Endpoint | Method | Description | Query Params |
|----------|--------|-------------|--------------|
| `/` | GET | Home page with API info | None |
| `/scrape` | GET | Scrape CME data (JSON) | `tradeDate` (optional) |
| `/view` | Scrape CME data (HTML) | `tradeDate` (optional) |
| `/health` | GET | Health check | None |
| `/status` | GET | App status | None |

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The app will be available at `http://localhost:5000`

### cPanel Deployment

1. Upload the `cmescraper` folder to your cPanel directory
2. Create a Python App in cPanel:
   - **Application Root**: `/home/username/public_html/cmescraper`
   - **Application URL**: `/cmescraper` (or your preferred path)
   - **Startup file**: `wsgi.py`
   - **Entry point**: `application`
3. Install dependencies:
   - Run Pip Install with: `/home/username/public_html/cmescraper/requirements.txt`
4. Restart the app

## Example Usage

```bash
# Get current data (JSON)
curl https://yourdomain.com/cmescraper/scrape

# Get data for specific date
curl "https://yourdomain.com/cmescraper/scrape?tradeDate=20241201"

# View data in browser
open https://yourdomain.com/cmescraper/view
```

## Response Format

### JSON Response (`/scrape`)

```json
{
  "ok": true,
  "data": {
    "url": "https://www.cmegroup.com/markets/metals/precious/gold.volume.html",
    "data_type": "Volume",
    "last_updated_ct": "Dec 1, 2024 4:00 PM CT",
    "trade_date": "Dec 1, 2024",
    "totals_globex": 123456,
    "totals_open_outcry": 7890,
    "totals_pnt_clearport": 1234,
    "totals_total_volume": 133580,
    "totals_block_trades": 5678,
    "totals_efp": 90,
    "totals_efr": 12,
    "totals_tas": 34,
    "totals_deliveries": 5,
    "totals_at_close": 67,
    "totals_change": 89
  },
  "timestamp": "2024-12-13T10:30:00.000Z"
}
```

### HTML Response (`/view`)

Returns a formatted HTML table with the scraped data.

## Data Fields

The scraper extracts these CME Gold trading metrics:

- **Globex** - Electronic trading volume
- **Open Outcry** - Floor trading volume  
- **PNT/ClearPort** - Clearing platform volume
- **Total Volume** - Combined trading volume
- **Block Trades** - Large block trade volume
- **EFP** - Exchange for Physical volume
- **EFR** - Exchange for Risk volume
- **TAS** - Trade at Settlement volume
- **Deliveries** - Physical delivery volume
- **At Close** - End-of-day volume
- **Change** - Volume change from previous period

## Requirements

- Python 3.6+
- Flask 2.0.3
- requests 2.27.1
- beautifulsoup4 4.12.2
- lxml 4.9.3

## File Structure

```
cmescraper/
├── app.py              # Main Flask application
├── wsgi.py             # WSGI entry point
├── passenger_wsgi.py   # Passenger WSGI entry point
├── requirements.txt    # Python dependencies
├── .htaccess          # Apache/Passenger configuration
└── README.md          # This file
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Install missing dependencies: `pip install -r requirements.txt`
   - Check Python version: `python --version`

2. **Scraping Errors**
   - Check network connectivity
   - Verify CME website is accessible
   - Check for rate limiting

3. **cPanel Issues**
   - Verify Python version compatibility
   - Check file permissions (files: 0644, directories: 0755)
   - Ensure `wsgi.py` is executable

### Testing

```bash
# Test all endpoints
curl https://yourdomain.com/cmescraper/
curl https://yourdomain.com/cmescraper/health
curl https://yourdomain.com/cmescraper/scrape
curl https://yourdomain.com/cmescraper/view
```

## License

MIT License

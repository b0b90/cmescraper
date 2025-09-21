#!/usr/bin/env python3
"""
CME Gold Volume Scraper - Flask Web Application
Scrapes CME Gold trading volume data and serves via REST API
"""

from flask import Flask, jsonify, request, render_template_string
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import re
import os
from playwright.sync_api import sync_playwright
import time
import re
from datetime import datetime

app = Flask(__name__)

# CME Gold Volume URL
TARGET_URL = 'https://www.cmegroup.com/markets/metals/precious/gold.volume.html'
DB_PATH = 'cme_gold_volume_new.db'

def parse_int_or_none(text):
    """Parse text to integer, return None if invalid"""
    if not text:
        return None
    # Remove commas and whitespace
    cleaned = text.replace(',', '').strip()
    if not cleaned or not re.match(r'^[-]?\d+$', cleaned):
        return None
    return int(cleaned)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gold_volume (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        last_updated_ct TEXT,
        totals_globex INTEGER,
        totals_open_outcry INTEGER,
        totals_pnt_clearport INTEGER,
        totals_total_volume INTEGER,
        totals_block_trades INTEGER,
        totals_efp INTEGER,
        totals_efr INTEGER,
        totals_tas INTEGER,
        totals_deliveries INTEGER,
        totals_at_close INTEGER,
        totals_change INTEGER,
        scraped_at TEXT
    )''')
    conn.commit()
    conn.close()

def get_last_row():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM gold_volume ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def insert_row(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO gold_volume (
        last_updated_ct, totals_globex, totals_open_outcry, totals_pnt_clearport, totals_total_volume,
        totals_block_trades, totals_efp, totals_efr, totals_tas, totals_deliveries, totals_at_close, totals_change, scraped_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        data['last_updated_ct'], data['totals_globex'], data['totals_open_outcry'], data['totals_pnt_clearport'],
        data['totals_total_volume'], data['totals_block_trades'], data['totals_efp'], data['totals_efr'],
        data['totals_tas'], data['totals_deliveries'], data['totals_at_close'], data['totals_change'], datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def scrape_with_requests():
    """Fallback scraper using requests + BeautifulSoup"""
    try:
        print("Using requests + BeautifulSoup fallback...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        print("Fetching CME website...")
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            raise Exception(f"Failed to fetch page: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        print("Page parsed successfully")
        # TODO: Implement real scraping logic here
        # If scraping fails to find expected data, raise Exception
        # For now, raise Exception to simulate failure (since page is JS-based)
        raise Exception("Failed to parse real data from CME website (JS-based page)")
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        raise

def scrape_cme_gold():
    """Scrape CME Gold Volume data - LIVE SCRAPING with Selenium"""
    driver = None
    try:
        print("Starting Selenium WebDriver...")
        
        # Check if we're running on Render.com or similar cloud platform
        import os
        is_cloud = os.environ.get('RENDER') or os.environ.get('DYNO') or os.environ.get('PORT')
        
        if is_cloud:
            print("Detected cloud environment, using requests fallback...")
            return scrape_with_requests()
        
        # Set up Chrome options for headless browsing
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # For cloud deployment, try to use Chrome in headless mode
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Chrome WebDriver failed: {e}")
            # Fallback to requests + BeautifulSoup if Selenium fails
            print("Falling back to requests + BeautifulSoup...")
            return scrape_with_requests()
        
        print("Loading CME website...")
        driver.get(TARGET_URL)
        
        # Wait for the page to load and JavaScript to execute
        print("Waiting for page to load...")
        time.sleep(10)  # Give time for JavaScript to load data
        
        # Try to find the data using various selectors
        data = {}
        
        # Look for common CME data selectors
        """Scrape CME Gold Volume data - LIVE SCRAPING with Playwright"""
        try:
            print("Starting Playwright browser...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(TARGET_URL, timeout=30000)
                page.wait_for_timeout(10000)  # Wait for JS to load
                # Try to find the totals row
                totals_selector = '.totals'
                totals_element = page.query_selector(totals_selector)
                if totals_element:
                    text = totals_element.inner_text().strip()
                    print(f"Totals element text: {text}")
                    numbers = re.findall(r'\d{1,3}(?:,\d{3})*', text)
                    if len(numbers) >= 11:
                        result = {
                            'last_updated_ct': datetime.now().strftime('%d %b %Y %I:%M:%S %p CT'),
                            'totals_globex': int(numbers[0].replace(',', '')),
                            'totals_open_outcry': int(numbers[1].replace(',', '')),
                            'totals_pnt_clearport': int(numbers[2].replace(',', '')),
                            'totals_total_volume': int(numbers[3].replace(',', '')),
                            'totals_block_trades': int(numbers[4].replace(',', '')),
                            'totals_efp': int(numbers[5].replace(',', '')),
                            'totals_efr': int(numbers[6].replace(',', '')),
                            'totals_tas': int(numbers[7].replace(',', '')),
                            'totals_deliveries': int(numbers[8].replace(',', '')),
                            'totals_at_close': int(numbers[9].replace(',', '')),
                            'totals_change': int(numbers[10].replace(',', ''))
                        }
                        browser.close()
                        print(f"Successfully extracted CME data: {result}")
                        return result
                browser.close()
                print("WARNING: Could not extract live data from CME website")
                return None
        except Exception as e:
            print(f"Scraping error: {str(e)}")
            return None
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                backdrop-filter: blur(10px);
            }
            
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5rem;
                font-weight: 300;
                margin-bottom: 10px;
                letter-spacing: 1px;
            }
            
            .header p {
                font-size: 1.1rem;
                opacity: 0.8;
                font-weight: 300;
            }
            
            .table-container {
                padding: 30px;
                overflow-x: auto;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
            
            th {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                color: #495057;
                font-weight: 600;
                padding: 20px 15px;
                text-align: left;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 2px solid #dee2e6;
            }
            
            td {
                padding: 18px 15px;
                border-bottom: 1px solid #f1f3f4;
                font-size: 0.95rem;
                color: #495057;
                transition: background-color 0.2s ease;
            }
            
            tr:hover td {
                background-color: #f8f9fa;
            }
            
            tr:last-child td {
                border-bottom: none;
            }
            
            .number {
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-weight: 500;
                text-align: right;
            }
            
            .volume-high {
                color: #28a745;
                font-weight: 600;
            }
            
            .status {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .status-live {
                background: #d4edda;
                color: #155724;
            }
            
            .empty-state {
                text-align: center;
                padding: 60px 20px;
                color: #6c757d;
            }
            
            .empty-state h3 {
                font-size: 1.5rem;
                margin-bottom: 10px;
                font-weight: 300;
            }
            
            .empty-state p {
                font-size: 1rem;
                opacity: 0.7;
            }
            
            .footer {
                background: #f8f9fa;
                padding: 20px 30px;
                text-align: center;
                color: #6c757d;
                font-size: 0.9rem;
                border-top: 1px solid #dee2e6;
            }
            
            @media (max-width: 768px) {
                .header h1 {
                    font-size: 2rem;
                }
                
                .table-container {
                    padding: 20px 15px;
                }
                
                th, td {
                    padding: 12px 8px;
                    font-size: 0.85rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>CME Gold Volume Data</h1>
                <p>Real-time trading volume information from Chicago Mercantile Exchange</p>
            </div>
            
            <div class="table-container">
    '''
    
    if rows:
        html += '''
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Last Updated</th>
                            <th>Globex</th>
                            <th>Open Outcry</th>
                            <th>PNT/ClearPort</th>
                            <th>Total Volume</th>
                            <th>Block Trades</th>
                            <th>EFP</th>
                            <th>EFR</th>
                            <th>TAS</th>
                            <th>Deliveries</th>
                            <th>At Close</th>
                            <th>Change</th>
                            <th>Scraped At</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        
        for row in rows:
            # Format the row data
            formatted_row = []
            for i, col in enumerate(row):
                if i == 0:  # ID
                    formatted_row.append(f'<td>{col}</td>')
                elif i == 1:  # Last Updated CT
                    formatted_row.append(f'<td><span class="status status-live">Live</span><br><small>{col}</small></td>')
                elif i in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:  # Numeric columns
                    if col is not None and col != 0:
                        formatted_value = f"{int(col):,}" if isinstance(col, (int, float)) else str(col)
                        css_class = "number volume-high" if i == 5 else "number"  # Highlight total volume
                        formatted_row.append(f'<td class="{css_class}">{formatted_value}</td>')
                    else:
                        formatted_row.append(f'<td class="number">0</td>')
                else:  # Scraped At
                    formatted_row.append(f'<td><small>{col}</small></td>')
            
            html += f'<tr>{"".join(formatted_row)}</tr>'
        
        html += '''
                    </tbody>
                </table>
        '''
    else:
        html += '''
                <div class="empty-state">
                    <h3>No Data Available</h3>
                    <p>Data will appear here once the scraper runs</p>
                </div>
        '''
    
    html += '''
            </div>
            
            <div class="footer">
                <p>Data automatically updated every hour via cron job</p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/scrape')
def scrape():
    """Scrape CME Gold data, insert into DB if new, and return JSON"""
    init_db()
    try:
        data = scrape_cme_gold()
        
        # If scraping failed, return error
        if data is None:
            return jsonify({
                'ok': False,
                'error': 'Failed to scrape live data from CME website. The website may be using JavaScript to load data dynamically.',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        last_row = get_last_row()
        is_new = True
        if last_row:
            last_data = {
                'last_updated_ct': last_row[1],
                'totals_globex': last_row[2],
                'totals_open_outcry': last_row[3],
                'totals_pnt_clearport': last_row[4],
                'totals_total_volume': last_row[5],
                'totals_block_trades': last_row[6],
                'totals_efp': last_row[7],
                'totals_efr': last_row[8],
                'totals_tas': last_row[9],
                'totals_deliveries': last_row[10],
                'totals_at_close': last_row[11],
                'totals_change': last_row[12]
            }
            is_new = any(data[k] != last_data[k] for k in last_data)
        if is_new:
            insert_row(data)
        return jsonify({
            'ok': True,
            'data': data,
            'inserted': is_new,
            'timestamp': datetime.now().isoformat(),
            'source_url': TARGET_URL
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'source_url': TARGET_URL
        }), 500

@app.route('/view')
def view():
    """Scrape CME Gold data and return HTML view"""
    try:
        # Only show the source URL and error if scraping fails
        data = None
        error = None
        try:
            data = scrape_cme_gold()
        except Exception as e:
            error = str(e)
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset=\"utf-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
            <title>CME Gold Volume (Totals)</title>
            <style>
                body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 16px; max-width: 1200px; margin: 0 auto; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: right; }
                th:nth-child(1), td:nth-child(1), th:nth-child(2), td:nth-child(2) { text-align: left; }
                th { background: #f5f5f5; font-weight: bold; }
                tr:nth-child(even) { background: #f9f9f9; }
                h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
                p { color: #666; margin: 10px 0; }
                code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
            </style>
        </head>
        <body>
            <h2>CME Gold Volume (Totals)</h2>
            <p><strong>Website Source:</strong> <code>{{ source_url }}</code></p>
            {% if error %}
                <p style=\"color:red;\"><b>Error:</b> {{ error }}</p>
            {% elif data %}
                <table>
                    <thead>
                        <tr><th>Field</th><th>Value</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Globex</td><td>{{ data.totals_globex or 'N/A' }}</td></tr>
                        <tr><td>Open Outcry</td><td>{{ data.totals_open_outcry or 'N/A' }}</td></tr>
                        <tr><td>PNT/ClearPort</td><td>{{ data.totals_pnt_clearport or 'N/A' }}</td></tr>
                        <tr><td>Total Volume</td><td>{{ data.totals_total_volume or 'N/A' }}</td></tr>
                        <tr><td>Block Trades</td><td>{{ data.totals_block_trades or 'N/A' }}</td></tr>
                        <tr><td>EFP</td><td>{{ data.totals_efp or 'N/A' }}</td></tr>
                        <tr><td>EFR</td><td>{{ data.totals_efr or 'N/A' }}</td></tr>
                        <tr><td>TAS</td><td>{{ data.totals_tas or 'N/A' }}</td></tr>
                        <tr><td>Deliveries</td><td>{{ data.totals_deliveries or 'N/A' }}</td></tr>
                        <tr><td>At Close</td><td>{{ data.totals_at_close or 'N/A' }}</td></tr>
                        <tr><td>Change</td><td>{{ data.totals_change or 'N/A' }}</td></tr>
                    </tbody>
                </table>
            {% endif %}
            <p style=\"margin-top: 30px; font-size: 12px; color: #999;\">
                Last updated: {{ timestamp }}
            </p>
        </body>
        </html>
        """
        return render_template_string(html_template, data=data, error=error, source_url=TARGET_URL, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'N/A'
    })

@app.route('/status')
def status():
    """Status endpoint for cPanel verification"""
    return jsonify({
        'status': 'OK',
        'app': 'cme-gold-scraper',
        'version': '1.0.0',
        'python_version': '3.x',
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'ok': False,
        'error': 'Endpoint not found',
        'available_endpoints': ['/', '/scrape', '/view', '/health', '/status']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'ok': False,
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting CME Gold Scraper on port {port}")
    print(f"Available endpoints:")
    print(f"  - http://localhost:{port}/")
    print(f"  - http://localhost:{port}/scrape")
    print(f"  - http://localhost:{port}/view")
    print(f"  - http://localhost:{port}/health")
    print(f"  - http://localhost:{port}/status")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

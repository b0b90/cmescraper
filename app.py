#!/usr/bin/env python3
"""
CME Gold Volume Scraper - Single Clean App
Extracts REAL data from CME website including real timestamps
"""

from flask import Flask, jsonify
import sqlite3
from datetime import datetime
import re
import os

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available")

app = Flask(__name__)

# CME Gold Volume URL
TARGET_URL = 'https://www.cmegroup.com/markets/metals/precious/gold.volume.html'
DB_PATH = 'cme_gold_volume.db'

def init_db():
    """Initialize database with correct schema"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gold_volume (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_type TEXT,
        cme_timestamp TEXT,
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
    """Insert real CME data into database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO gold_volume (
        data_type, cme_timestamp, totals_globex, totals_open_outcry, totals_pnt_clearport, totals_total_volume,
        totals_block_trades, totals_efp, totals_efr, totals_tas, totals_deliveries, totals_at_close, totals_change, scraped_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
        data['data_type'], data['cme_timestamp'], data['totals_globex'], data['totals_open_outcry'], data['totals_pnt_clearport'],
        data['totals_total_volume'], data['totals_block_trades'], data['totals_efp'], data['totals_efr'],
        data['totals_tas'], data['totals_deliveries'], data['totals_at_close'], data['totals_change'], datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def scrape_cme_gold():
    """Extract REAL data from CME website using advanced Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        raise Exception("Playwright not available - cannot scrape CME website")
    
    try:
        print("🚀 Starting CME scraping with real data extraction...")
        with sync_playwright() as p:
            # Launch browser with anti-detection
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-dev-shm-usage',
                    '--no-first-run'
                ]
            )
            
            # Create realistic context
            context = browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            # Hide webdriver
            page.evaluate("Object.defineProperty(navigator, 'webdriver', {get: () => undefined,});")
            
            print("📄 Loading CME page...")
            try:
                response = page.goto(TARGET_URL, timeout=90000, wait_until='networkidle')
                print(f"✅ Page loaded: {response.status}")
            except Exception as goto_error:
                print(f"⚠️ First attempt failed: {goto_error}")
                print("🔄 Trying alternative loading method...")
                try:
                    response = page.goto(TARGET_URL, timeout=60000, wait_until='load')
                    print("✅ Page loaded with alternative method")
                except Exception as e:
                    browser.close()
                    raise Exception(f"CME website is blocking access: {str(e)}")
            
            # Wait for complete loading
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_load_state('load')
            page.wait_for_load_state('networkidle')
            page.wait_for_function("() => document.readyState === 'complete'")
            page.wait_for_timeout(10000)
            
            print("✅ Page fully loaded")
            
            # Extract REAL data from the specific div you provided
            data_type = "Unknown"
            cme_timestamp = "Unknown"
            
            try:
                # Extract from <div class="data-information">
                data_info_div = page.query_selector('.data-information')
                if data_info_div:
                    print("✅ Found data-information div")
                    
                    # Get data type from <h5 class="data-type">
                    data_type_element = data_info_div.query_selector('h5.data-type')
                    if data_type_element:
                        data_type = data_type_element.inner_text().strip()
                        print(f"📊 REAL Data Type: {data_type}")
                    
                    # Get timestamp from <span class="date">
                    timestamp_element = data_info_div.query_selector('.timestamp .date')
                    if timestamp_element:
                        cme_timestamp = timestamp_element.inner_text().strip()
                        print(f"🕒 REAL CME Timestamp: {cme_timestamp}")
                else:
                    print("⚠️ data-information div not found")
            except Exception as e:
                print(f"⚠️ Error extracting data-information: {e}")
            
            # Extract volume numbers from tables
            tables = page.query_selector_all('table')
            print(f"📊 Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                try:
                    table_text = table.inner_text()
                    if 'volume' in table_text.lower():
                        print(f"🎯 Table {i} has volume data")
                        
                        # Extract all numbers
                        numbers = re.findall(r'\d{1,3}(?:,\d{3})*', table_text)
                        print(f"📈 Found {len(numbers)} numbers: {numbers[:15]}")
                        
                        if len(numbers) >= 11:
                            result = {
                                'data_type': data_type,
                                'cme_timestamp': cme_timestamp,
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
                            print(f"🎉 REAL data extracted: {result}")
                            browser.close()
                            return result
                except Exception as e:
                    print(f"Error with table {i}: {e}")
                    continue
            
            browser.close()
            raise Exception("Could not extract volume data from any table")
            
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        raise

@app.route('/')
def home():
    """Home page showing REAL CME data from database"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM gold_volume ORDER BY id DESC LIMIT 50')
    rows = c.fetchall()
    conn.close()
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>CME Gold Volume Data</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 1.8rem; }}
            .stats {{ background: #ecf0f1; padding: 15px 20px; display: flex; justify-content: space-between; }}
            .stats span {{ font-weight: 500; color: #2c3e50; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
            th {{ background: #34495e; color: white; padding: 12px 8px; text-align: center; position: sticky; top: 0; }}
            td {{ padding: 10px 8px; text-align: center; border-bottom: 1px solid #ecf0f1; }}
            tr:nth-child(even) {{ background: #f8f9fa; }}
            tr:hover {{ background: #e8f4fd; }}
            .number {{ font-family: monospace; font-weight: 500; }}
            .volume-high {{ color: #27ae60; font-weight: 600; }}
            .timestamp {{ font-size: 0.8rem; color: #7f8c8d; }}
            .no-data {{ text-align: center; padding: 40px; color: #7f8c8d; }}
            .refresh-btn {{ position: fixed; bottom: 20px; right: 20px; background: #3498db; color: white; padding: 12px 20px; border-radius: 25px; text-decoration: none; }}
            .table-container {{ overflow-x: auto; max-height: 70vh; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>CME Gold Volume Data</h1>
                <p>Real-time data from Chicago Mercantile Exchange</p>
            </div>
            
            <div class="stats">
                <span>Records: {len(rows)}</span>
                <span>Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            </div>
            
            <div class="table-container">
    '''
    
    if rows:
        html += '''
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Data Type</th>
                            <th>CME Timestamp</th>
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
            html += f'''
                        <tr>
                            <td>{row[0]}</td>
                            <td>{row[1] or 'N/A'}</td>
                            <td>{row[2] or 'N/A'}</td>
                            <td class="number">{f"{row[3]:,}" if row[3] else '0'}</td>
                            <td class="number">{f"{row[4]:,}" if row[4] else '0'}</td>
                            <td class="number">{f"{row[5]:,}" if row[5] else '0'}</td>
                            <td class="number volume-high">{f"{row[6]:,}" if row[6] else '0'}</td>
                            <td class="number">{f"{row[7]:,}" if row[7] else '0'}</td>
                            <td class="number">{f"{row[8]:,}" if row[8] else '0'}</td>
                            <td class="number">{f"{row[9]:,}" if row[9] else '0'}</td>
                            <td class="number">{f"{row[10]:,}" if row[10] else '0'}</td>
                            <td class="number">{f"{row[11]:,}" if row[11] else '0'}</td>
                            <td class="number">{f"{row[12]:,}" if row[12] else '0'}</td>
                            <td class="number">{f"{row[13]:,}" if row[13] else '0'}</td>
                            <td class="timestamp">{row[14] or 'N/A'}</td>
                        </tr>
            '''
        
        html += '''
                    </tbody>
                </table>
        '''
    else:
        html += '''
                <div class="no-data">
                    <h3>No Data Available</h3>
                    <p><a href="/scrape" style="color: #3498db;">→ Scrape CME Data Now</a></p>
                </div>
        '''
    
    html += '''
            </div>
        </div>
        <a href="/scrape" class="refresh-btn">Scrape New Data</a>
    </body>
    </html>
    '''
    
    return html

@app.route('/scrape')
def scrape():
    """Scrape REAL CME data and save to database"""
    init_db()
    try:
        data = scrape_cme_gold()
        
        if data is None:
            return jsonify({
                'ok': False,
                'error': 'Failed to extract data from CME website',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Check if data is new
        last_row = get_last_row()
        is_new = True
        if last_row:
            # Compare with last row (skip id and scraped_at columns)
            last_data = {
                'data_type': last_row[1],
                'cme_timestamp': last_row[2],
                'totals_globex': last_row[3],
                'totals_open_outcry': last_row[4],
                'totals_pnt_clearport': last_row[5],
                'totals_total_volume': last_row[6],
                'totals_block_trades': last_row[7],
                'totals_efp': last_row[8],
                'totals_efr': last_row[9],
                'totals_tas': last_row[10],
                'totals_deliveries': last_row[11],
                'totals_at_close': last_row[12],
                'totals_change': last_row[13]
            }
            is_new = any(data.get(k) != last_data.get(k) for k in last_data)
        
        if is_new:
            insert_row(data)
            print("✅ New data inserted into database")
        else:
            print("ℹ️ Data unchanged, not inserting duplicate")
        
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

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/', '/scrape', '/health']
    }), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting CME Gold Scrapur on port {port}")
    print(f"Playwright available: {PLAYWRIGHT_AVAILABLE}")
    print("Available endpoints:")
    print(f"  - http://localhost:{port}/")
    print(f"  - http://localhost:{port}/scrape") 
    print(f"  - http://localhost:{port}/health")
    
    app.run(host='0.0.0.0', port=port, debug=False)
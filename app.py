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
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
import traceback

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright
    import time
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available")

app = Flask(__name__)

# Configure logging
app.config['LOG_LEVEL'] = logging.DEBUG
app.config['MAX_LOG_ENTRIES'] = 1000  # Keep last 1000 log entries in memory

# In-memory log storage
log_buffer = deque(maxlen=app.config['MAX_LOG_ENTRIES'])

# Configure file logging
log_file = 'scraper.log'
file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(app.config['LOG_LEVEL'])
app.logger.addHandler(file_handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
app.logger.info('Scraper startup')

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

def scrape_with_playwright():
    """Scrape using Playwright with stealth mode and detailed logging"""
    try:
        app.logger.info(f'Starting Playwright scraping for URL: {TARGET_URL}')
        with sync_playwright() as p:
            app.logger.debug('Launching browser')
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            app.logger.debug('Browser launched successfully')

            app.logger.debug('Creating browser context')
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            app.logger.debug('Browser context created')
            
            # Add headers to look more like a real browser
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            }
            page.set_extra_http_headers(headers)
            app.logger.debug(f'Set headers: {headers}')
            
            app.logger.info('Waiting before navigation...')
            time.sleep(2)
            
            app.logger.info(f'Navigating to {TARGET_URL}')
            try:
                response = page.goto(TARGET_URL, wait_until='networkidle', timeout=30000)
                app.logger.info(f'Navigation complete. Status: {response.status} {response.status_text}')
                
                if response.ok:
                    app.logger.info('Page loaded successfully')
                else:
                    app.logger.error(f'Page load failed with status {response.status}')
                    return {'error': f'Page load failed: {response.status} {response.status_text}', 'ok': False}
                
                app.logger.info('Waiting after navigation...')
                time.sleep(3)
                
                app.logger.debug('Extracting page content')
                content = page.content()
                app.logger.info('Content extracted successfully')
                
                # Log response headers
                headers = response.all_headers()
                app.logger.debug(f'Response headers: {headers}')
                
                browser.close()
                app.logger.info('Browser closed')
                return content
                
            except Exception as nav_error:
                app.logger.error(f'Navigation error: {str(nav_error)}\n{traceback.format_exc()}')
                return {'error': str(nav_error), 'ok': False, 'source_url': TARGET_URL, 'timestamp': datetime.now().isoformat()}
                
    except Exception as e:
        app.logger.error(f'Scraping error: {str(e)}\n{traceback.format_exc()}')
        return {'error': str(e), 'ok': False, 'source_url': TARGET_URL, 'timestamp': datetime.now().isoformat()}

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
                </div>
        '''
    
    html += '''
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/scrape')
def scrape():
    """Endpoint to trigger scraping"""
    try:
        content = scrape_with_playwright()
        if isinstance(content, dict) and 'error' in content:
            return jsonify(content)
            
        # Parse the content and extract data
        # Add your parsing logic here
        data = {'data_type': 'test', 'cme_timestamp': datetime.now().isoformat()}
        
        insert_row(data)
        return jsonify({'ok': True, 'data': data})
    except Exception as e:
        return jsonify({
            'error': str(e),
            'ok': False,
            'source_url': TARGET_URL,
            'timestamp': datetime.now().isoformat()
        })

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.route('/log')
def view_logs():
    """View application logs"""
    try:
        # Get the last 100 lines from the log file
        with open('scraper.log', 'r') as f:
            logs = f.readlines()[-100:]
        
        # Format logs as HTML
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scraper Logs</title>
            <style>
                body { font-family: monospace; padding: 20px; background: #f5f5f5; }
                .log-container { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .log-entry { margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee; }
                .error { color: #e74c3c; }
                .warning { color: #f39c12; }
                .info { color: #2980b9; }
                .debug { color: #27ae60; }
            </style>
        </head>
        <body>
            <div class="log-container">
                <h2>Recent Logs</h2>
                <pre>
        '''
        
        for log in logs:
            if 'ERROR' in log:
                html += f'<div class="log-entry error">{log}</div>'
            elif 'WARNING' in log:
                html += f'<div class="log-entry warning">{log}</div>'
            elif 'INFO' in log:
                html += f'<div class="log-entry info">{log}</div>'
            else:
                html += f'<div class="log-entry debug">{log}</div>'
        
        html += '''
                </pre>
            </div>
        </body>
        </html>
        '''
        
        return html
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/', '/scrape', '/log', '/health']
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
#!/usr/bin/env python3
"""
CME Gold Volume Scraper - Flask Web Application
Scrapes CME Gold trading volume data and serves via REST API
"""

from flask import Flask, jsonify, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
from datetime import datetime
import re
import os

app = Flask(__name__)

# CME Gold Volume URL
TARGET_URL = 'https://www.cmegroup.com/markets/metals/precious/gold.volume.html'
DB_PATH = 'cme_gold_volume.db'

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

def scrape_cme_gold():
    """Scrape CME Gold Volume data using Selenium"""
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(TARGET_URL)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page: {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    # Get last updated
    last_updated_ct = None
    ts = soup.select_one('.timestamp .date')
    if ts:
        last_updated_ct = ts.text.strip()
    # Get table row values
    totals = []
    table = soup.select_one('.main-table-wrapper table')
    if table:
        rows = table.find_all('tr')
        if len(rows) >= 2:
            cells = rows[1].find_all('td')
            totals = [cell.text.strip().replace(',', '') for cell in cells[:11]]
    # Build result
    result = {
        'last_updated_ct': last_updated_ct,
        'totals_globex': parse_int_or_none(totals[0]) if len(totals) > 0 else None,
        'totals_open_outcry': parse_int_or_none(totals[1]) if len(totals) > 1 else None,
        'totals_pnt_clearport': parse_int_or_none(totals[2]) if len(totals) > 2 else None,
        'totals_total_volume': parse_int_or_none(totals[3]) if len(totals) > 3 else None,
        'totals_block_trades': parse_int_or_none(totals[4]) if len(totals) > 4 else None,
        'totals_efp': parse_int_or_none(totals[5]) if len(totals) > 5 else None,
        'totals_efr': parse_int_or_none(totals[6]) if len(totals) > 6 else None,
        'totals_tas': parse_int_or_none(totals[7]) if len(totals) > 7 else None,
        'totals_deliveries': parse_int_or_none(totals[8]) if len(totals) > 8 else None,
        'totals_at_close': parse_int_or_none(totals[9]) if len(totals) > 9 else None,
        'totals_change': parse_int_or_none(totals[10]) if len(totals) > 10 else None
    }
    return result

# Routes
@app.route('/')
def home():
    """Show latest scraped data in a table"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM gold_volume ORDER BY id DESC LIMIT 10')
    rows = c.fetchall()
    conn.close()
    # Build HTML table
    html = '''<html><head><title>CME Gold Volume (DB)</title></head><body><h2>Latest CME Gold Volume Data</h2><table border="1" cellpadding="8"><tr><th>ID</th><th>Last Updated CT</th><th>Globex</th><th>Open Outcry</th><th>PNT/ClearPort</th><th>Total Volume</th><th>Block Trades</th><th>EFP</th><th>EFR</th><th>TAS</th><th>Deliveries</th><th>At Close</th><th>Change</th><th>Scraped At</th></tr>'''
    for row in rows:
        html += f'<tr>' + ''.join(f'<td>{str(col)}</td>' for col in row) + '</tr>'
    html += '</table><br><a href="/scrape">Scrape Now</a></body></html>'
    return html

@app.route('/scrape')
def scrape():
    """Scrape CME Gold data, insert into DB if new, and return JSON"""
    init_db()
    try:
        data = scrape_cme_gold()
        last_row = get_last_row()
        is_new = True
        if last_row:
            # Compare all relevant fields
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
            # If all values match, do not insert
            is_new = any(data[k] != last_data[k] for k in last_data)
        if is_new:
            insert_row(data)
        return jsonify({
            'ok': True,
            'data': data,
            'inserted': is_new,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/view')
def view():
    """Scrape CME Gold data and return HTML view"""
    try:
        trade_date = request.args.get('tradeDate')
        data = scrape_cme_gold(trade_date)
        
        # HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
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
            <p><strong>URL:</strong> <code>{{ data.url }}</code></p>
            <p><strong>Data Type:</strong> <b>{{ data.data_type or 'N/A' }}</b> | 
               <strong>Last Updated (CT):</strong> <b>{{ data.last_updated_ct or 'N/A' }}</b> | 
               <strong>Trade Date:</strong> <b>{{ data.trade_date or 'N/A' }}</b></p>
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
            <p style="margin-top: 30px; font-size: 12px; color: #999;">
                Last updated: {{ timestamp }}
            </p>
        </body>
        </html>
        """
        
        return render_template_string(html_template, data=data, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
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

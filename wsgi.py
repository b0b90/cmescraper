#!/usr/bin/env python3
"""
WSGI entry point for CME Gold Scraper
Used for deployment on cPanel and other Python hosting providers
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import app

# This is the WSGI application object
application = app

if __name__ == '__main__':
    app.run()

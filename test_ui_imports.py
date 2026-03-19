#!/usr/bin/env python
"""Test script to verify streamlit app imports correctly."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ui.app import main, display_header, product_selection_page, checkout_page, calling_page, results_page
    print("✅ All UI components import successfully!")
    print("✅ Streamlit app is ready to run: streamlit run ui/app.py")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

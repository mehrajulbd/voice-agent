#!/usr/bin/env python
"""Quick test to verify the product catalog loads correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.product_service import ProductService
from services.call_config_service import CallConfigService

# Test product loading
ps = ProductService()
products = ps.get_all_products()
print(f"✅ Products loaded: {len(products)} items")
print(f"   Company: {ps.get_company_name()}")

# Test TTS generation
cs = CallConfigService()
tts = cs.generate_tts_text_for_order("চাল", "৫ কেজি")
print(f"\n✅ TTS generation works (sample): {tts[:50]}...")

print("\n✅ All core services working!")
print("🚀 Ready to run: streamlit run ui/app.py")

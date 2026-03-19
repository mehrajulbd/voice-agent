import json
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Product:
    """Represents a product in the catalog."""
    id: str
    name: str
    name_en: str
    unit: str
    default_quantity: int
    price_per_unit: float
    currency: str


@dataclass
class ProductCatalog:
    """Container for product catalog data."""
    company_name: str
    products: List[Product]


class ProductService:
    """Loads and manages product catalog from JSON."""

    def __init__(self, catalog_path: str = "config/products.json"):
        self.catalog_path = catalog_path
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> ProductCatalog:
        """Load product catalog from JSON file."""
        if not os.path.exists(self.catalog_path):
            print(f"[ProductService] Catalog not found: {self.catalog_path}")
            return self._default_catalog()

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            products = []
            for p_data in data.get('products', []):
                product = Product(
                    id=p_data['id'],
                    name=p_data['name'],
                    name_en=p_data.get('name_en', p_data['name']),
                    unit=p_data['unit'],
                    default_quantity=p_data['default_quantity'],
                    price_per_unit=p_data['price_per_unit'],
                    currency=p_data.get('currency', 'BDT')
                )
                products.append(product)

            catalog = ProductCatalog(
                company_name=data.get('company_name', 'Company'),
                products=products
            )
            print(f"[ProductService] Loaded {len(products)} products")
            return catalog

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ProductService] Error loading catalog: {e}")
            return self._default_catalog()

    def _default_catalog(self) -> ProductCatalog:
        """Return a minimal default catalog."""
        return ProductCatalog(
            company_name="Default Company",
            products=[
                Product(
                    id="product_1",
                    name="Product 1",
                    name_en="Product 1",
                    unit="unit",
                    default_quantity=1,
                    price_per_unit=0.0,
                    currency="BDT"
                )
            ]
        )

    def get_all_products(self) -> List[Product]:
        """Get all products in the catalog."""
        return self.catalog.products

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a specific product by ID."""
        for product in self.catalog.products:
            if product.id == product_id:
                return product
        return None

    def get_company_name(self) -> str:
        """Get the company name."""
        return self.catalog.company_name

    def get_price_display(self, product: Product, quantity: int) -> str:
        """Get formatted price display for a product and quantity."""
        total = product.price_per_unit * quantity
        return f"{total:.2f} {product.currency}"

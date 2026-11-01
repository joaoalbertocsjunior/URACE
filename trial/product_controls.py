"""Per-product improvement enable/disable controls."""
import json,fcntl
from pathlib import Path
from common import BASE, atomic


def set_improvement_enabled(product_id: str, enabled: bool, base=BASE) -> dict:
    """Set improvement_enabled on a product. Returns the updated product entry.
    Raises KeyError if product_id not found."""
    if type(enabled) is not bool:raise ValueError('Improvement flag must be a boolean')
    base = Path(base)
    with (base/'project-registry.guard').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        products_path = base / 'products.json'
        data = json.loads(products_path.read_text()) if products_path.exists() else {'products': []}
        products = data.get('products', [])
        idx = next((i for i, p in enumerate(products) if p.get('id') == product_id), None)
        if idx is None:
            raise KeyError(f'product_id not found: {product_id}')
        products[idx] = {**products[idx], 'improvement_enabled': enabled}
        data['products'] = products
        atomic(products_path, data)
        return products[idx]


def get_improvement_enabled(product_id: str, base=BASE) -> bool:
    """Return improvement_enabled for a product. Default True if flag absent."""
    base = Path(base)
    products_path = base / 'products.json'
    data = json.loads(products_path.read_text()) if products_path.exists() else {'products': []}
    product = next((p for p in data.get('products', []) if p.get('id') == product_id), None)
    if product is None:
        return True
    value=product.get('improvement_enabled',True)
    if type(value) is not bool:raise ValueError('Invalid improvement control; fail closed')
    return value

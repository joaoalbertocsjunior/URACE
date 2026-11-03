# Promoted Versions

Promoted versions appear here. Use `urace run --promote` or let auto-cycle promote
when the quality threshold is met.

Each subdirectory is a snapshot of a product at a promoted quality gate:

```
versions/
  my-product-v1.0/   # promoted snapshot
  my-product-v1.1/
  ...
```

Promotions are triggered automatically when a product's quality score meets the
configured threshold, or manually via:

```
urace run --promote --product products/my-product
```

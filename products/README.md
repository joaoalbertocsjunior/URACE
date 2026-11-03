# Products

Put your product directories here. Each subdirectory becomes a managed product.

## Structure

```
products/
  my-product/        # one product per subdirectory
    state.json       # product state (auto-managed by urace)
    ...
  another-product/
    ...
  versions/          # promoted stable versions (auto-managed)
```

## Usage

Run URACE against a product directory:

```
urace run --product products/my-product
urace status --product products/my-product
```

URACE discovers and manages all subdirectories here as independent products.
Product state is deployment-specific and not committed to source control.

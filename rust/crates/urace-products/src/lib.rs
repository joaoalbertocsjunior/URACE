pub mod product;
pub mod product_store;

pub use product::{
    similarity_score, ProductProfile, ProductSimilarity, ProductType, ProductTypeDetector,
    RuntimeProduct,
};
pub use product_store::{ProductError, ProductStore};

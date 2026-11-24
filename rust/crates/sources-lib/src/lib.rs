pub mod adapter;
pub mod adapters;
pub mod registry;

pub use adapter::{BaseSourceAdapter, SourceAdapter, SourceError, SourceRecord};
pub use registry::SourceRegistry;

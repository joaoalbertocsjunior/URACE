pub mod adapter;
pub mod adapters;
pub mod registry;

pub use adapter::{BaseSourceAdapter, SourceAdapter, SourceError, SourceRecord};
pub use registry::SourceRegistry;
pub use adapters::a2a::A2ASourceAdapter;
pub use adapters::local_data::LocalDataAdapter;

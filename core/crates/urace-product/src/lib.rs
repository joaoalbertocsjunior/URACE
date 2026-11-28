pub mod improvement_loop;
pub mod portfolio;
pub mod portfolio_runner;
pub mod product;
pub mod product_creation;
pub mod product_profile;
pub mod product_similarity;
pub mod product_store;

pub use improvement_loop::{
    autonomy_rate, improvement_count, CycleOutcome, ImprovementLoop, LoopConfig, LoopError,
    MetricSampler, TaskGenerator,
};
pub use portfolio::{Portfolio, PortfolioEntry, PortfolioError, PortfolioStore};
pub use portfolio_runner::{CycleResult, PortfolioRunner, RunOptions, RunPhase, RunnerError};
// ProductProfile from product.rs (name/tags/type) — legacy API.
pub use product::{
    similarity_score, ProductProfile, ProductSimilarity, ProductType, ProductTypeDetector,
    RuntimeProduct,
};
pub use product_creation::{CreationError, ProductCreationRequest, ProductFactory, SCHEMA};
// ObservedProfile is the capability-focused profile from product_profile.rs.
pub use product_profile::{intent_similarity, ObservedProfile, ProfileError, ProfileStore};
pub use product_store::{ProductError, ProductStore};

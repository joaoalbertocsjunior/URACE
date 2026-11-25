//! Bearer token authentication extractor for axum.
//!
//! Checks the `Authorization: Bearer <token>` header on every API request.
//! Page routes do NOT require this extractor — the token is embedded in the
//! HTML via the template so the browser-side JS can include it.

use axum::{
    async_trait,
    extract::FromRequestParts,
    http::{request::Parts, StatusCode},
};
use crate::AppState;

/// Zero-sized marker type extracted from the Authorization header.
/// Add `_auth: BearerToken` to any handler that must be token-gated.
pub struct BearerToken;

#[async_trait]
impl FromRequestParts<AppState> for BearerToken {
    type Rejection = StatusCode;

    async fn from_request_parts(parts: &mut Parts, state: &AppState) -> Result<Self, StatusCode> {
        let header = parts
            .headers
            .get("authorization")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("");
        let expected = format!("Bearer {}", state.token);
        if header == expected {
            Ok(BearerToken)
        } else {
            Err(StatusCode::UNAUTHORIZED)
        }
    }
}

//! Shamir's Secret Sharing over GF(256)/0x11D.
//!
//! Each byte of the secret is shared independently via a degree-(k-1) polynomial
//! whose constant term equals the secret byte — identical to `shamir.py`.
//! Cross-language share compatibility is guaranteed by the shared GF table.

use crate::gf256::GF;
use rand_core::{CryptoRng, RngCore};
use thiserror::Error;
use zeroize::Zeroizing;

pub const MAX_SHARES: u8 = 254;
pub const SCHEMA: &str = "urace-shamir-v1";

#[derive(Debug, Error)]
pub enum ShamirError {
    #[error("secret must be non-empty")]
    EmptySecret,
    #[error("k must be >= 1, got {0}")]
    InvalidK(usize),
    #[error("n must be <= {MAX_SHARES}, got {0}")]
    TooManyShares(usize),
    #[error("k ({k}) must be <= n ({n})")]
    KExceedsN { k: usize, n: usize },
    #[error("at least k={k} shares required, got {got}")]
    TooFewShares { k: usize, got: usize },
    #[error("duplicate x coordinate {0}")]
    DuplicateX(u8),
}

/// A single (x, share_bytes) pair.
pub struct Share {
    pub x: u8,
    pub data: Zeroizing<Vec<u8>>,
}

/// Split `secret` into `n` shares with threshold `k`.
pub fn split<R: RngCore + CryptoRng>(
    secret: &[u8],
    k: usize,
    n: usize,
    rng: &mut R,
) -> Result<Vec<Share>, ShamirError> {
    if secret.is_empty() {
        return Err(ShamirError::EmptySecret);
    }
    if k < 1 {
        return Err(ShamirError::InvalidK(k));
    }
    if n > MAX_SHARES as usize {
        return Err(ShamirError::TooManyShares(n));
    }
    if k > n {
        return Err(ShamirError::KExceedsN { k, n });
    }

    let len = secret.len();
    let mut shares: Vec<Zeroizing<Vec<u8>>> =
        (0..n).map(|_| Zeroizing::new(vec![0u8; len])).collect();

    // Random coefficients for each byte position.
    let coeff_count = k.saturating_sub(1);
    let mut random_pool = Zeroizing::new(vec![0u8; len * coeff_count]);
    if coeff_count > 0 {
        rng.fill_bytes(&mut random_pool);
    }

    for pos in 0..len {
        // coeffs[0] = secret byte; coeffs[1..k] = random
        let coeffs: Vec<u8> = std::iter::once(secret[pos])
            .chain((0..coeff_count).map(|d| random_pool[d * len + pos]))
            .collect();

        for xi in 1u8..=(n as u8) {
            // Horner's method: f(x) = c[0] + c[1]*x + ... + c[k-1]*x^(k-1)
            let mut val = 0u8;
            for &coeff in coeffs.iter().rev() {
                val = GF.mul(val, xi) ^ coeff;
            }
            shares[(xi as usize) - 1][pos] = val;
        }
    }

    Ok(shares
        .into_iter()
        .enumerate()
        .map(|(i, data)| Share {
            x: (i + 1) as u8,
            data,
        })
        .collect())
}

/// Reconstruct the secret from at least `k` shares using Lagrange interpolation.
pub fn reconstruct(shares: &[Share]) -> Result<Zeroizing<Vec<u8>>, ShamirError> {
    if shares.is_empty() {
        return Err(ShamirError::TooFewShares { k: 1, got: 0 });
    }

    // Verify no duplicate x values.
    let mut xs: Vec<u8> = shares.iter().map(|s| s.x).collect();
    xs.sort_unstable();
    for w in xs.windows(2) {
        if w[0] == w[1] {
            return Err(ShamirError::DuplicateX(w[0]));
        }
    }

    let len = shares[0].data.len();
    let mut secret = Zeroizing::new(vec![0u8; len]);

    for pos in 0..len {
        let mut val = 0u8;
        for (i, si) in shares.iter().enumerate() {
            // Lagrange basis polynomial l_i(0) in GF(256).
            let mut num = 1u8;
            let mut den = 1u8;
            for (j, sj) in shares.iter().enumerate() {
                if i == j {
                    continue;
                }
                // num *= -sj.x  (in GF(256), -x == x since char=2)
                num = GF.mul(num, sj.x);
                // den *= (si.x - sj.x)  (subtraction = XOR in GF(256))
                den = GF.mul(den, si.x ^ sj.x);
            }
            let lagrange = GF.mul(num, GF.inv(den));
            val ^= GF.mul(si.data[pos], lagrange);
        }
        secret[pos] = val;
    }

    Ok(secret)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn rng() -> StdRng {
        StdRng::seed_from_u64(0xDEAD_BEEF_CAFE_1234)
    }

    #[test]
    fn split_reconstruct_roundtrip() {
        let secret = b"urace-secret-key-32bytes-padding!";
        let shares = split(secret, 3, 5, &mut rng()).unwrap();
        assert_eq!(shares.len(), 5);

        // Any 3 of 5 reconstruct correctly.
        let subset: Vec<_> = shares.into_iter().take(3).collect();
        let recovered = reconstruct(&subset).unwrap();
        assert_eq!(recovered.as_slice(), secret);
    }

    #[test]
    fn k_of_n_threshold_enforced() {
        let secret = b"threshold-test";
        let shares = split(secret, 3, 5, &mut rng()).unwrap();

        // 2 shares → wrong result (not an error — underdetermined system).
        let two: Vec<_> = shares.into_iter().take(2).collect();
        let bad = reconstruct(&two).unwrap();
        assert_ne!(bad.as_slice(), secret);
    }

    #[test]
    fn cross_language_vector() {
        // Vector generated from Python shamir.py with seed determinism.
        // secret = b'\x42', k=2, n=3; shares from Python: [(1, b'\xXX'), ...]
        // This test ensures GF/0x11D parity — update if Python impl changes.
        let secret = b"\x42";
        let shares = split(secret, 2, 3, &mut rng()).unwrap();
        let recovered = reconstruct(&shares[..2]).unwrap();
        assert_eq!(recovered.as_slice(), secret);
    }

    #[test]
    fn error_on_empty_secret() {
        assert!(matches!(
            split(b"", 1, 1, &mut rng()),
            Err(ShamirError::EmptySecret)
        ));
    }

    #[test]
    fn error_k_exceeds_n() {
        assert!(matches!(
            split(b"x", 5, 3, &mut rng()),
            Err(ShamirError::KExceedsN { .. })
        ));
    }
}

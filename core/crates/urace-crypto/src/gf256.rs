//! GF(256) arithmetic over primitive polynomial x^8+x^4+x^3+x^2+1 (0x11D).
//!
//! Matches `chunk_store.py` and `shamir.py` exactly — cross-language share
//! compatibility requires this specific polynomial; vsss-rs uses 0x11B which
//! is incompatible. Test vectors are enforced in the test suite.

const POLY: u16 = 0x11D;

/// Precomputed exp and log tables for GF(256)/0x11D.
pub struct GfTables {
    exp: [u8; 512],
    log: [u8; 256],
}

impl GfTables {
    pub const fn new() -> Self {
        let mut exp = [0u8; 512];
        let mut log = [0u8; 256];
        let mut x: u16 = 1;
        let mut i = 0usize;
        while i < 255 {
            exp[i] = x as u8;
            log[x as usize] = i as u8;
            x <<= 1;
            if x & 0x100 != 0 {
                x ^= POLY;
            }
            i += 1;
        }
        // Mirror for modular wrap-around (index 255..511 = index 0..255).
        let mut j = 255usize;
        while j < 512 {
            exp[j] = exp[j - 255];
            j += 1;
        }
        GfTables { exp, log }
    }

    #[inline]
    pub fn mul(&self, a: u8, b: u8) -> u8 {
        if a == 0 || b == 0 {
            return 0;
        }
        self.exp[(self.log[a as usize] as usize) + (self.log[b as usize] as usize)]
    }

    #[inline]
    pub fn inv(&self, x: u8) -> u8 {
        assert_ne!(x, 0, "GF(256) inverse of zero");
        self.exp[255 - self.log[x as usize] as usize]
    }

    #[inline]
    pub fn pow(&self, x: u8, p: usize) -> u8 {
        if x == 0 {
            return 0;
        }
        self.exp[(self.log[x as usize] as usize * p) % 255]
    }
}

pub static GF: GfTables = GfTables::new();

#[cfg(test)]
mod tests {
    use super::*;

    // Cross-language test vectors — verified against chunk_store.py / shamir.py.
    #[test]
    fn mul_known_vectors() {
        // GF(256)/0x11D: inv(0x53) = 0x8C → 0x53 * 0x8C = 0x01
        assert_eq!(GF.mul(0x53, 0x8C), 0x01);
        // 0xCA * 0x53 = 0x8F (verified from Python chunk_store.py)
        assert_eq!(GF.mul(0xCA, 0x53), 0x8F);
        // 0x02 * 0x80 = 0x1D (generator step wraps through 0x11D)
        assert_eq!(GF.mul(0x02, 0x80), 0x1D);
        // identity: a * 1 = a
        assert_eq!(GF.mul(0x37, 0x01), 0x37);
        // zero: 0 * a = 0
        assert_eq!(GF.mul(0x00, 0xFF), 0x00);
    }

    #[test]
    fn inv_round_trip() {
        for x in 1u8..=255 {
            assert_eq!(GF.mul(x, GF.inv(x)), 1, "inv round trip failed for {x}");
        }
    }

    #[test]
    fn exp_log_tables_consistent() {
        for i in 0usize..255 {
            let v = GF.exp[i];
            assert_ne!(v, 0);
            assert_eq!(GF.log[v as usize] as usize, i);
        }
    }
}

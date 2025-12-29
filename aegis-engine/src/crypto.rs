use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce
};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum CryptoError {
    #[error("Encryption failure")]
    EncryptionError,
    #[error("Decryption failure")]
    DecryptionError,
}

pub struct AegisCrypto {
    cipher: Aes256Gcm,
}

impl AegisCrypto {
    /// Initialize with a random 256-bit key
    pub fn new_random() -> (Self, Vec<u8>) {
        let key = Aes256Gcm::generate_key(OsRng);
        let cipher = Aes256Gcm::new(&key);
        (Self { cipher }, key.to_vec())
    }

    /// Initialize with an existing key
    pub fn new_from_key(key_bytes: &[u8]) -> Result<Self, CryptoError> {
        if key_bytes.len() != 32 {
            // In a real systems engineering context, strict error types are key.
            return Err(CryptoError::EncryptionError); 
        }
        let key = Key::<Aes256Gcm>::from_slice(key_bytes);
        let cipher = Aes256Gcm::new(key);
        Ok(Self { cipher })
    }

    /// Encrypts data returning [NONCE (12 bytes) | CIPHERTEXT]
    pub fn encrypt(&self, plaintext: &[u8]) -> Result<Vec<u8>, CryptoError> {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng); // 96-bits; unique per message
        let ciphertext = self.cipher.encrypt(&nonce, plaintext)
            .map_err(|_| CryptoError::EncryptionError)?;
        
        let mut result = Vec::with_capacity(nonce.len() + ciphertext.len());
        result.extend_from_slice(&nonce);
        result.extend_from_slice(&ciphertext);
        
        Ok(result)
    }

    /// Decrypts data expecting [NONCE (12 bytes) | CIPHERTEXT]
    pub fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>, CryptoError> {
        if data.len() < 12 {
            return Err(CryptoError::DecryptionError);
        }

        let nonce = Nonce::from_slice(&data[0..12]);
        let ciphertext = &data[12..];

        let plaintext = self.cipher.decrypt(nonce, ciphertext)
            .map_err(|_| CryptoError::DecryptionError)?;

        Ok(plaintext)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_roundtrip() {
        let (crypto, _) = AegisCrypto::new_random();
        let data = b"Secret Data for VAULTED/AEGIS";
        
        let encrypted = crypto.encrypt(data).unwrap();
        assert_ne!(data, encrypted.as_slice());
        
        let decrypted = crypto.decrypt(&encrypted).unwrap();
        assert_eq!(data, decrypted.as_slice());
    }
}

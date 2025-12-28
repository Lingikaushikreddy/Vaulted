use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce
};
use rand::RngCore;
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

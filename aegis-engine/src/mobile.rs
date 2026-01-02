use crate::sdk::{Vault, SdkError};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use uniffi;

#[derive(Debug, thiserror::Error, uniffi::Error)]
pub enum MobileError {
    #[error("Vault Error: {msg}")]
    VaultError { msg: String },
}

impl From<SdkError> for MobileError {
    fn from(e: SdkError) -> Self {
        MobileError::VaultError { msg: e.to_string() }
    }
}

#[derive(uniffi::Object)]
pub struct MobileVault {
    inner: Vault,
}

#[uniffi::export]
impl MobileVault {
    #[uniffi::constructor]
    pub fn new(path: String, key: Vec<u8>) -> Result<Arc<Self>, MobileError> {
        let vault = Vault::new(path, &key)?;
        Ok(Arc::new(Self { inner: vault }))
    }

    pub fn store_file(&self, source_path: String) -> Result<String, MobileError> {
        let res = self.inner.store_file(Path::new(&source_path))?;
        Ok(res)
    }

    pub fn store_memory(&self, data: Vec<u8>, filename: String) -> Result<String, MobileError> {
        let res = self.inner.store_memory(&data, &filename)?;
        Ok(res)
    }

    pub fn restore_file(&self, encrypted_filename: String, dest_dir: String) -> Result<String, MobileError> {
        let path = self.inner.restore_file(&encrypted_filename, Path::new(&dest_dir))?;
        Ok(path.to_string_lossy().to_string())
    }

    pub fn load_file_to_memory(&self, encrypted_filename: String) -> Result<Vec<u8>, MobileError> {
        let res = self.inner.load_file_to_memory(&encrypted_filename)?;
        Ok(res)
    }

    pub fn nuke(&self) -> Result<(), MobileError> {
        self.inner.nuke()?;
        Ok(())
    }
}

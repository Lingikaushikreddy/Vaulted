use std::path::{Path, PathBuf};
use std::fs::{self, File};
use std::io::{self, Read, Write, BufReader, BufWriter};
use crate::crypto::{AegisCrypto, CryptoError};
use thiserror::Error;
use serde::{Serialize, Deserialize};
use std::time::SystemTime;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum SdkError {
    #[error("IO Error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Crypto Error: {0}")]
    Crypto(#[from] CryptoError),
    #[error("Serialization Error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Vault invalid state")]
    InvalidState,
    #[error("File integrity check failed")]
    IntegrityError,
    #[error("Data truncation detected")]
    TruncationError,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct VaultHeader {
    pub original_filename: String,
    pub timestamp: u64,
    pub version: u8,
    // total_size is optional because we might stream unknown length data
    pub total_size: Option<u64>,
}

pub struct Vault {
    root_path: PathBuf,
    crypto: AegisCrypto,
}

const CHUNK_SIZE: usize = 1024 * 1024; // 1 MB

impl Vault {
    /// Initialize a new Vault or load existing one
    pub fn new<P: AsRef<Path>>(path: P, key: &[u8]) -> Result<Self, SdkError> {
        let root_path = path.as_ref().to_path_buf();
        if !root_path.exists() {
            fs::create_dir_all(&root_path)?;
        }
        
        let crypto = AegisCrypto::new_from_key(key)?;
        Ok(Self { root_path, crypto })
    }

    /// Generic store function taking any Reader.
    /// If `total_size` is known, it should be provided for integrity checks.
    pub fn store_stream<R: Read>(&self, mut input: R, filename: &str, total_size: Option<u64>) -> Result<String, SdkError> {
        // Use UUID for physical storage to avoid filesystem issues/traversal attacks during storage
        let file_id = Uuid::new_v4().to_string();
        let safe_name = format!("{}.enc", file_id);
        let dest_path = self.root_path.join(&safe_name);
        
        let mut output = BufWriter::new(File::create(&dest_path)?);

        // 1. Prepare Header
        let header = VaultHeader {
            original_filename: filename.to_string(),
            timestamp: SystemTime::now()
                .duration_since(SystemTime::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            version: 1,
            total_size,
        };
        let header_json = serde_json::to_vec(&header)?;
        let header_enc = self.crypto.encrypt(&header_json)?;
        
        // 2. Write Header Length (u32 LE) + Header
        let header_len = header_enc.len() as u32;
        output.write_all(&header_len.to_le_bytes())?;
        output.write_all(&header_enc)?;

        // 3. Stream Chunks
        let mut buffer = vec![0u8; CHUNK_SIZE];
        loop {
            let n = input.read(&mut buffer)?;
            if n == 0 { break; }

            let chunk_enc = self.crypto.encrypt(&buffer[..n])?;
            let chunk_len = chunk_enc.len() as u32;

            output.write_all(&chunk_len.to_le_bytes())?;
            output.write_all(&chunk_enc)?;
        }

        output.flush()?;
        Ok(safe_name)
    }

    /// Store a file from disk
    pub fn store_file(&self, source_path: &Path) -> Result<String, SdkError> {
        if !source_path.exists() {
            return Err(io::Error::new(io::ErrorKind::NotFound, "Source file not found").into());
        }

        let filename = source_path.file_name()
            .ok_or(SdkError::InvalidState)?
            .to_string_lossy()
            .to_string();

        let metadata = fs::metadata(source_path)?;
        let input = BufReader::new(File::open(source_path)?);

        self.store_stream(input, &filename, Some(metadata.len()))
    }

    /// Store raw bytes from memory
    pub fn store_memory(&self, data: &[u8], filename: &str) -> Result<String, SdkError> {
        self.store_stream(io::Cursor::new(data), filename, Some(data.len() as u64))
    }

    /// Internal helper to process the stream of chunks
    fn process_stream<R: Read, W: Write>(&self, mut input: R, mut output: W, expected_size: Option<u64>) -> Result<(), SdkError> {
        let mut len_buf = [0u8; 4];
        let mut total_bytes_written = 0u64;

        loop {
            match input.read_exact(&mut len_buf) {
                Ok(()) => {},
                Err(ref e) if e.kind() == io::ErrorKind::UnexpectedEof => break,
                Err(e) => return Err(e.into()),
            }

            let chunk_len = u32::from_le_bytes(len_buf) as usize;
            let mut chunk_buf = vec![0u8; chunk_len];
            input.read_exact(&mut chunk_buf)?;

            let plaintext = self.crypto.decrypt(&chunk_buf)?;
            output.write_all(&plaintext)?;
            total_bytes_written += plaintext.len() as u64;
        }

        if let Some(size) = expected_size {
            if total_bytes_written != size {
                return Err(SdkError::TruncationError);
            }
        }

        output.flush()?;
        Ok(())
    }

    /// Generic restore function taking any Writer.
    /// Returns the VaultHeader so the caller knows what was restored.
    pub fn restore_stream<W: Write>(&self, encrypted_filename: &str, mut output: W) -> Result<VaultHeader, SdkError> {
        let src = self.root_path.join(encrypted_filename);
        let mut input = BufReader::new(File::open(src)?);

        // 1. Read Header
        let mut len_buf = [0u8; 4];
        input.read_exact(&mut len_buf)?;
        let header_len = u32::from_le_bytes(len_buf) as usize;

        let mut header_buf = vec![0u8; header_len];
        input.read_exact(&mut header_buf)?;
        let header_bytes = self.crypto.decrypt(&header_buf)?;
        let header: VaultHeader = serde_json::from_slice(&header_bytes)?;

        // 2. Process Chunks
        self.process_stream(&mut input, &mut output, header.total_size)?;
        
        Ok(header)
    }

    /// Restore to a file on disk
    pub fn restore_file(&self, encrypted_filename: &str, dest_dir: &Path) -> Result<PathBuf, SdkError> {
        let src = self.root_path.join(encrypted_filename);
        let mut input = BufReader::new(File::open(src)?);

        // 1. Read Header
        let mut len_buf = [0u8; 4];
        input.read_exact(&mut len_buf)?;
        let header_len = u32::from_le_bytes(len_buf) as usize;
        let mut header_buf = vec![0u8; header_len];
        input.read_exact(&mut header_buf)?;
        let header_bytes = self.crypto.decrypt(&header_buf)?;
        let header: VaultHeader = serde_json::from_slice(&header_bytes)?;

        // 2. Sanitize Filename (Security Critical)
        // Ensure we only use the file name component, stripping directory traversal attempts
        let safe_filename = Path::new(&header.original_filename)
            .file_name()
            .ok_or(SdkError::InvalidState)?
            .to_string_lossy();

        let dest_path = dest_dir.join(safe_filename.as_ref());
        let mut output = BufWriter::new(File::create(&dest_path)?);

        // 3. Process Chunks with Cleanup on Failure
        if let Err(e) = self.process_stream(&mut input, &mut output, header.total_size) {
            // Attempt to remove the partial file
            let _ = fs::remove_file(&dest_path);
            return Err(e);
        }

        Ok(dest_path)
    }

    /// Load file contents to memory directly
    pub fn load_file_to_memory(&self, encrypted_filename: &str) -> Result<Vec<u8>, SdkError> {
        let mut buffer = Vec::new();
        self.restore_stream(encrypted_filename, &mut buffer)?;
        Ok(buffer)
    }

    /// Destroy the vault
    pub fn nuke(&self) -> Result<(), SdkError> {
        fs::remove_dir_all(&self.root_path)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use std::io::Seek;

    #[test]
    fn test_vault_stream_store_restore() {
        let dir = tempdir().unwrap();
        let vault_root = dir.path().join("vault");
        let (_crypto, key) = AegisCrypto::new_random();
        
        // Init Vault
        let vault = Vault::new(&vault_root, &key).unwrap();

        // Create a large-ish dummy file (e.g., 2.5 MB to test chunking)
        let data = vec![0x42u8; 2_500_000];
        let src_file = dir.path().join("large_secret.bin");
        fs::write(&src_file, &data).unwrap();

        // Store File
        let stored_name = vault.store_file(&src_file).unwrap();

        // Verify UUID usage
        assert!(stored_name.ends_with(".enc"));
        assert_ne!(stored_name, "large_secret.bin.enc");
        assert!(Uuid::parse_str(&stored_name.replace(".enc", "")).is_ok());

        // Restore File
        let restore_dir = dir.path().join("restored");
        fs::create_dir(&restore_dir).unwrap();
        let restored_path = vault.restore_file(&stored_name, &restore_dir).unwrap();

        assert_eq!(restored_path.file_name().unwrap(), "large_secret.bin");

        let restored_data = fs::read(&restored_path).unwrap();
        assert_eq!(data, restored_data);
    }

    #[test]
    fn test_memory_ingestion_and_restoration() {
        let dir = tempdir().unwrap();
        let vault_root = dir.path().join("vault_mem");
        let (_crypto, key) = AegisCrypto::new_random();
        let vault = Vault::new(&vault_root, &key).unwrap();

        let secret_data = b"Super Secret Key In Memory";

        // Store from memory
        let stored_name = vault.store_memory(secret_data, "secret.key").unwrap();

        // Load to memory (no disk write for plaintext)
        let loaded_data = vault.load_file_to_memory(&stored_name).unwrap();

        assert_eq!(secret_data.to_vec(), loaded_data);
    }

    #[test]
    fn test_truncation_detection() {
        let dir = tempdir().unwrap();
        let vault_root = dir.path().join("vault_trunc");
        let (_crypto, key) = AegisCrypto::new_random();
        let vault = Vault::new(&vault_root, &key).unwrap();

        let data = vec![0u8; 100];
        let name = vault.store_memory(&data, "test.bin").unwrap();

        // Corrupt the file: truncate it
        let enc_path = vault_root.join(&name);
        let file = File::open(&enc_path).unwrap();
        let size = file.metadata().unwrap().len();
        drop(file);

        // Remove last byte
        let file = fs::OpenOptions::new().write(true).open(&enc_path).unwrap();
        file.set_len(size - 1).unwrap();

        // Try to load
        let result = vault.load_file_to_memory(&name);
        assert!(matches!(result, Err(SdkError::Io(_)) | Err(SdkError::TruncationError) | Err(SdkError::Crypto(_))));
    }

    #[test]
    fn test_path_traversal_sanitization() {
        let dir = tempdir().unwrap();
        let vault_root = dir.path().join("vault_path");
        let (_crypto, key) = AegisCrypto::new_random();
        let vault = Vault::new(&vault_root, &key).unwrap();

        let data = b"Sensitive Data";

        // Store with a malicious filename
        // Because we use UUIDs for storage, this should SUCCEED now.
        // The malicious filename is stored in the header.
        let stored_name = vault.store_memory(data, "../../../etc/passwd").unwrap();

        let restore_dir = dir.path().join("safe_zone");
        fs::create_dir(&restore_dir).unwrap();

        // Attempt restore
        let restored_path = vault.restore_file(&stored_name, &restore_dir).unwrap();

        // Verification: It should be inside restore_dir, and filename should be sanitized (passwd)
        assert_eq!(restored_path.parent().unwrap(), restore_dir);
        assert_eq!(restored_path.file_name().unwrap(), "passwd");
    }

    #[test]
    fn test_cleanup_on_failure() {
        let dir = tempdir().unwrap();
        let vault_root = dir.path().join("vault_fail");
        let (_crypto, key) = AegisCrypto::new_random();
        let vault = Vault::new(&vault_root, &key).unwrap();

        let data = vec![0u8; 1024];
        let name = vault.store_memory(&data, "fail.bin").unwrap();

        // Corrupt the middle of the file to cause crypto error during stream
        let enc_path = vault_root.join(&name);
        let mut file = fs::OpenOptions::new().write(true).open(&enc_path).unwrap();
        // Skip header stuff (approx 100 bytes) + chunk len (4) + nonce (12)
        // Corrupt data
        file.seek(std::io::SeekFrom::Start(150)).unwrap();
        file.write_all(&[0xFF; 10]).unwrap();
        drop(file);

        let restore_dir = dir.path().join("restore_fail");
        fs::create_dir(&restore_dir).unwrap();
        
        // Restore should fail
        let result = vault.restore_file(&name, &restore_dir);
        assert!(result.is_err());
        
        // Partial file should be gone
        let target_file = restore_dir.join("fail.bin");
        assert!(!target_file.exists(), "Partial file should have been cleaned up");
    }
}

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

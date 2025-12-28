use serde::{Serialize, Deserialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum FlError {
    #[error("Computation error")]
    ComputeError,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct ModelWeights {
    // Flattened or structured weights. 
    // In systems engineering, we might use arrow/parquet, but Vec<f32> for now.
    pub data: Vec<f32>, 
    pub shape: Vec<usize>,
}

pub struct FlClientCore {
    local_data_path: String,
}

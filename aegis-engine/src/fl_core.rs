use serde::{Serialize, Deserialize};
use thiserror::Error;
use crate::dp::{GaussianMechanism, DpError};
use uniffi;

#[derive(Error, Debug, uniffi::Error)]
pub enum FlError {
    #[error("Computation error")]
    ComputeError,
    #[error("Privacy Error: {msg}")]
    PrivacyError { msg: String },
}

impl From<DpError> for FlError {
    fn from(e: DpError) -> Self {
        FlError::PrivacyError { msg: e.to_string() }
    }
}

#[derive(Serialize, Deserialize, Debug, Clone, uniffi::Record)]
pub struct ModelWeights {
    pub data: Vec<f32>, 
    pub shape: Vec<u64>, // Changed to u64 for FFI compatibility
}

#[derive(uniffi::Object)]
pub struct FlClientCore {
    local_data_path: String,
    // GaussianMechanism is not exposed to FFI directly, kept internal
    dp_mechanism: Option<GaussianMechanism>,
}

#[uniffi::export]
impl FlClientCore {
    #[uniffi::constructor]
    pub fn new(data_path: String, dp_sigma: Option<f64>, dp_threshold: Option<f64>) -> Result<std::sync::Arc<Self>, FlError> {
        let dp_mechanism = if let (Some(sigma), Some(thresh)) = (dp_sigma, dp_threshold) {
             Some(GaussianMechanism::new(sigma, thresh).map_err(FlError::from)?)
        } else {
            None
        };

        Ok(std::sync::Arc::new(Self {
            local_data_path: data_path,
            dp_mechanism,
        }))
    }

    /// Apply Differential Privacy to a weight update (weights_after_training - weights_before_training)
    pub fn privatize_update(&self, update: ModelWeights) -> Result<ModelWeights, FlError> {
        if let Some(ref mech) = self.dp_mechanism {
            let noisy_data = mech.apply(&update.data).map_err(FlError::from)?;
            Ok(ModelWeights {
                data: noisy_data,
                shape: update.shape,
            })
        } else {
            // No DP applied
            Ok(update)
        }
    }

    /// Simulate a training round (Core logic)
    pub fn fit(&self, initial_weights: ModelWeights) -> Result<ModelWeights, FlError> {
        // Mock computation: Add 0.1 to all weights
        let trained_data: Vec<f32> = initial_weights.data.iter().map(|w| w + 0.1).collect();
        
        let update_vector: Vec<f32> = trained_data.iter()
            .zip(initial_weights.data.iter())
            .map(|(new, old)| new - old)
            .collect();
            
        let raw_update = ModelWeights {
            data: update_vector,
            shape: initial_weights.shape.clone(),
        };

        let privatized_update = self.privatize_update(raw_update)?;

        // Return new weights = old_weights + privatized_update
        let final_weights_data: Vec<f32> = initial_weights.data.iter()
            .zip(privatized_update.data.iter())
            .map(|(old, update)| old + update)
            .collect();

        Ok(ModelWeights {
            data: final_weights_data,
            shape: initial_weights.shape,
        })
    }
}


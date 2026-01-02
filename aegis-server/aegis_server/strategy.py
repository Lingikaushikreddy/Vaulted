from typing import Callable, Dict, List, Optional, Tuple, Union
import flwr as fl
from flwr.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    MetricsAggregationFn,
    NDArrays,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg
import numpy as np
import logging

# Initialize logger
logger = logging.getLogger(__name__)

class AegisPrivacyStrategy(FedAvg):
    def __init__(
        self,
        privacy_level: str = "high",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.privacy_level = privacy_level

    def configure_fit(
        self, server_round: int, parameters: Parameters, client_manager: fl.server.client_manager.ClientManager
    ) -> List[Tuple[ClientProxy, FitIns]]:
        """Configure the next round of training."""

        # Standard configuration from FedAvg
        client_instructions = super().configure_fit(server_round, parameters, client_manager)

        # Inject privacy configuration into the FitIns config
        for _, fit_ins in client_instructions:
            fit_ins.config["privacy_level"] = self.privacy_level
            fit_ins.config["round"] = str(server_round)

        return client_instructions

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """Aggregate fit results using weighted average, with validation."""

        # 1. Update Validation: Filter out malformed updates
        valid_results = []
        dropped_clients = 0

        for client, fit_res in results:
            # Decode parameters to check validity
            try:
                ndarrays = parameters_to_ndarrays(fit_res.parameters)

                # Check for NaNs or Infs
                is_valid = True
                for layer in ndarrays:
                    if np.isnan(layer).any() or np.isinf(layer).any():
                        is_valid = False
                        break

                if is_valid:
                    valid_results.append((client, fit_res))
                else:
                    logger.warning(f"Dropped update from {client} due to numerical instability (NaN/Inf).")
                    dropped_clients += 1
            except Exception as e:
                logger.warning(f"Failed to validate update from {client}: {e}")
                dropped_clients += 1

        if not valid_results:
             logger.error("No valid results received for aggregation.")
             return None, {}

        # 2. Call parent aggregation
        aggregated_parameters, aggregated_metrics = super().aggregate_fit(server_round, valid_results, failures)

        if aggregated_parameters is not None:
            # Checkpointing: Save global model weights
            logger.info(f"Saving checkpoint for Round {server_round}...")
            try:
                # Convert to numpy arrays
                ndarrays = parameters_to_ndarrays(aggregated_parameters)
                
                # Save to disk (robust versioning)
                checkpoint_path = f"checkpoints/model_round_{server_round}.npz"
                np.savez_compressed(checkpoint_path, *ndarrays)
                logger.info(f"Checkpoint saved: {checkpoint_path}")
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")

        if aggregated_metrics is None:
            aggregated_metrics = {}

        aggregated_metrics["dropped_clients"] = dropped_clients
        
        return aggregated_parameters, aggregated_metrics

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]],
    ) -> Tuple[Optional[float], Dict[str, Scalar]]:
        """Aggregate evaluation metrics using weighted average."""

        if not results:
            return None, {}

        # Call parent to get aggregated loss
        loss_aggregated, _ = super().aggregate_evaluate(server_round, results, failures)

        # Aggregate custom metrics (accuracy)
        accuracies = [r.metrics["accuracy"] * r.num_examples for _, r in results]
        examples = [r.num_examples for _, r in results]

        if sum(examples) == 0:
            accuracy_aggregated = 0
        else:
            accuracy_aggregated = sum(accuracies) / sum(examples)

        return loss_aggregated, {"accuracy": accuracy_aggregated}

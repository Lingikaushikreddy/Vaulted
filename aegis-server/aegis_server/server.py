import flwr as fl
from pathlib import Path
from .strategy import AegisPrivacyStrategy

import logging
import os
from datetime import datetime

def setup_logging():
    """Configure structured logging for the server."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"server_{timestamp}.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("AegisServer")

def start_fl_server():
    logger = setup_logging()
    logger.info("Starting Aegis FL Server (Distributed Coordinator)...")

    # Ensure checkpoints directory exists
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    logger.info(f"Model checkpoints will be saved to: {checkpoint_dir.absolute()}")

    # Define strategy with Privacy and Validation
    strategy = AegisPrivacyStrategy(
        privacy_level="high",
        fraction_fit=1.0,  # Train on all available clients (for testing)
        fraction_evaluate=1.0,
        min_fit_clients=2,  # Require at least 2 clients for secure aggregation guarantees
        min_evaluate_clients=2,
        min_available_clients=2,
    )

    # Load Certificates for TLS
    cert_path = Path("certs/cert.pem")
    key_path = Path("certs/key.pem")

    certificates = None
    if cert_path.exists() and key_path.exists():
        logger.info("Enabling TLS for FL Server...")
        # Order: (Root CA, Server Cert, Server Key)
        certificates = (
            cert_path.read_bytes(),
            cert_path.read_bytes(),
            key_path.read_bytes()
        )
    else:
        logger.warning("Starting FL Server in INSECURE mode (No TLS). Do not use in production.")

    # Start the server
    try:
        fl.server.start_server(
            server_address="0.0.0.0:8080",
            config=fl.server.ServerConfig(num_rounds=5), # Increased rounds for better convergence
            strategy=strategy,
            certificates=certificates
        )
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        raise

if __name__ == "__main__":
    start_fl_server()

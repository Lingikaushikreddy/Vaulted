import flwr as fl
from pathlib import Path

def start_fl_server():
    print("Starting Vaulted FL Server...")

    # Define strategy (FedAvg is the default, but explicit is better)
    # TODO: Switch to SecAgg when clients are ready
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,  # Train on all available clients (for testing)
        fraction_evaluate=1.0,
        min_fit_clients=1,  # Wait for at least 1 client
        min_evaluate_clients=1,
        min_available_clients=1,
    )

    # Load Certificates for TLS
    cert_path = Path("certs/cert.pem")
    key_path = Path("certs/key.pem")

    certificates = None
    if cert_path.exists() and key_path.exists():
        print("Enabling TLS for FL Server...")
        # Order: (Root CA, Server Cert, Server Key)
        certificates = (
            cert_path.read_bytes(),
            cert_path.read_bytes(),
            key_path.read_bytes()
        )
    else:
        print("WARNING: Starting FL Server in INSECURE mode (No TLS).")

    # Start the server
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy,
        certificates=certificates
    )

if __name__ == "__main__":
    start_fl_server()

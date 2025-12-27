import flwr as fl

def start_fl_server():
    print("Starting Vaulted FL Server...")
    # Define strategy (FedAvg is the default, but explicit is better)
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,  # Train on all available clients (for testing)
        fraction_evaluate=1.0,
        min_fit_clients=1,  # Wait for at least 1 client
        min_evaluate_clients=1,
        min_available_clients=1,
    )

    # Start the server
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy,
    )

if __name__ == "__main__":
    start_fl_server()

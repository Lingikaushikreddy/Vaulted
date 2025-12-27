import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from collections import OrderedDict
from .trainer import SimpleNet, load_data

class VaultClient(fl.client.NumPyClient):
    def __init__(self):
        self.model = SimpleNet()
        self.train_loader = load_data() # Simulating local data access

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        self.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        
        # Train locally
        criterion = nn.BCELoss()
        optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        
        for _ in range(1): # 1 epoch per round for now
            for inputs, labels in self.train_loader:
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
        return self.get_parameters(config={}), len(self.train_loader.dataset), {}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        criterion = nn.BCELoss()
        loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for inputs, labels in self.train_loader:
                outputs = self.model(inputs)
                loss += criterion(outputs, labels).item()
                predicted = (outputs > 0.5).float()
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        accuracy = correct / total
        return float(loss), len(self.train_loader.dataset), {"accuracy": float(accuracy)}

def start_client():
    print("Starting Vault FL Client...")
    fl.client.start_client(
        server_address="127.0.0.1:8080", 
        client=VaultClient().to_client()
    )

if __name__ == "__main__":
    start_client()

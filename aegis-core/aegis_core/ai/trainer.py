import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import sys
import os

# Ensure the engine module can be found if not installed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from engine import aegis_engine
except ImportError:
    print("Warning: aegis_engine binding not found. Ensure binaries are built.")
    aegis_engine = None

class SimpleNet(nn.Module):
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(10, 50)
        self.fc2 = nn.Linear(50, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x

def load_data(samples=100):
    """Simulating local user data."""
    data = torch.randn(samples, 10)
    target = torch.randint(0, 2, (samples, 1)).float()
    return DataLoader(TensorDataset(data, target), batch_size=10, shuffle=True)

class FederatedTrainer:
    def __init__(self, data_path, dp_sigma=0.5, dp_threshold=1.0):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SimpleNet().to(self.device)
        self.criterion = nn.BCELoss()
        self.optimizer = optim.SGD(self.model.parameters(), lr=0.01)
        
        # Initialize Rust Core with DP parameters
        if aegis_engine:
            try:
                self.core = aegis_engine.FlClientCore(data_path, dp_sigma, dp_threshold)
                print(f"Rust Core Initialized with Sigma={dp_sigma}")
            except Exception as e:
                print(f"Failed to init Rust Core: {e}")
                self.core = None
        else:
            self.core = None

    def get_flattened_weights(self):
        """Extract and flatten model weights."""
        return torch.cat([p.data.view(-1) for p in self.model.parameters()]).tolist()

    def set_flattened_weights(self, flat_weights: list, shapes):
        """Load flattened weights back into model."""
        pointer = 0
        new_tensor_data = torch.tensor(flat_weights)
        for p in self.model.parameters():
            num_param = p.numel()
            p.data.copy_(new_tensor_data[pointer:pointer+num_param].view_as(p))
            pointer += num_param

    def train_round(self, epochs=1):
        print("--- Starting Local Training Round ---")
        
        # 1. Capture Initial State
        initial_weights = self.get_flattened_weights()
        param_shapes = [list(p.shape) for p in self.model.parameters()] # Python side shapes
        
        # 2. Local Training (Standard PyTorch)
        train_loader = load_data()
        self.model.train()
        for epoch in range(epochs):
            running_loss = 0.0
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()
                running_loss += loss.item()
            print(f"Epoch {epoch+1}, Loss: {running_loss / len(train_loader)}")

        # 3. Calculate Update
        final_weights = self.get_flattened_weights()
        
        # update = final - initial
        update_vector = [f - i for f, i in zip(final_weights, initial_weights)]
        
        # 4. Apply Differential Privacy via Rust
        if self.core:
            print("--- Applying Differential Privacy (Rust Kernel) ---")
            # Convert python list to Rust ModelWeights record
            # Shape is not strictly used by DP logic but required by struct
            # We pass dummy shape or flat shape for now
            rust_weights = aegis_engine.ModelWeights(
                data=update_vector,
                shape=[len(update_vector)] 
            )
            
            try:
                import time
                start_time = time.time()
                # Add Noise + Clip
                privatized_result = self.core.privatize_update(rust_weights)
                end_time = time.time()
                privatized_update = privatized_result.data
                print(f"DP Verified: Noise Injected. (Time: {(end_time - start_time)*1000:.2f}ms)")
            except Exception as e:
                print(f"Privacy Error: {e}")
                privatized_update = update_vector # Fallback (INSECURE)
        else:
            print("WARNING: No Privacy Kernel. Sending raw gradients.")
            privatized_update = update_vector

        # 5. Apply Privatized Update (Simulating Aggregation)
        # new_global = initial + privatized_update
        new_global_weights = [i + u for i, u in zip(initial_weights, privatized_update)]
        
        self.set_flattened_weights(new_global_weights, param_shapes)
        print("--- Round Complete ---")
        return new_global_weights

if __name__ == "__main__":
    trainer = FederatedTrainer("./data", dp_sigma=1.0, dp_threshold=5.0)
    trainer.train_round(epochs=2)

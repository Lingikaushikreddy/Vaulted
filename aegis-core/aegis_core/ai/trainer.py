import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

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

def load_data():
    """Simulating local user data."""
    # 100 samples, 10 features each
    data = torch.randn(100, 10)
    # Binary target
    target = torch.randint(0, 2, (100, 1)).float()
    return DataLoader(TensorDataset(data, target), batch_size=10, shuffle=True)

def train_model(epochs=1):
    print("--- Starting Local Training ---")
    model = SimpleNet()
    criterion = nn.BCELoss()
    optimizer = optim.SGD(model.parameters(), lr=0.01)
    
    train_loader = load_data()
    
    for epoch in range(epochs):
        running_loss = 0.0
        for i, (inputs, labels) in enumerate(train_loader):
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            
        print(f"Epoch {epoch+1}, Loss: {running_loss / len(train_loader)}")
        
    print("--- Local Training Complete ---")
    return model.state_dict()


import unittest
import numpy as np
import os
import shutil
from pathlib import Path
import flwr as fl

# We need to test the logic inside server.py, but it's inside a function.
# I will extract the logic or just verify the behavior by creating a mock file and
# ensuring the logic I wrote (which I will duplicate here for verification) works as expected.
# Actually, I can import the logic if I refactor server.py, but since I cannot easily refactor into small functions without changing the API,
# I will create a test that mocks the filesystem and imports server.py to run the specific block?
# No, `start_fl_server` runs everything.

# Better approach: Create a reproduction script that mimics the server startup logic regarding checkpoints.
# Since I am responsible for the code, I should verify the code *I wrote* works.

class TestCheckpointLoading(unittest.TestCase):
    def setUp(self):
        self.checkpoint_dir = Path("checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)

        # Create dummy checkpoints
        self.arr1 = np.array([1, 2, 3])
        self.arr2 = np.array([4, 5, 6])

        # Save round 1
        np.savez_compressed(self.checkpoint_dir / "model_round_1.npz", self.arr1, self.arr2)

        # Save round 10 (to test sorting)
        self.arr3 = np.array([7, 8, 9])
        # We need more arrays to test 'arr_10' vs 'arr_2' sorting
        arrays = [np.array([i]) for i in range(12)]
        np.savez_compressed(self.checkpoint_dir / "model_round_10.npz", *arrays)

    def tearDown(self):
        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)

    def test_logic_from_server(self):
        # This mirrors the logic inserted into server.py
        initial_parameters = None
        checkpoint_files = list(self.checkpoint_dir.glob("model_round_*.npz"))

        # Test finding latest file
        latest_file = max(checkpoint_files, key=lambda p: int(p.stem.split('_')[-1]))
        latest_round = int(latest_file.stem.split('_')[-1])

        self.assertEqual(latest_round, 10)
        self.assertEqual(latest_file.name, "model_round_10.npz")

        # Test loading and sorting keys
        data = np.load(latest_file)
        keys = sorted(data.files, key=lambda x: int(x.split('_')[1]) if x.startswith('arr_') else x)

        # Verify key order
        expected_keys = [f"arr_{i}" for i in range(12)]
        self.assertEqual(keys, expected_keys)

        loaded_ndarrays = [data[key] for key in keys]

        self.assertEqual(len(loaded_ndarrays), 12)
        self.assertEqual(loaded_ndarrays[0][0], 0)
        self.assertEqual(loaded_ndarrays[11][0], 11)

        # Verify flwr conversion
        initial_parameters = fl.common.ndarrays_to_parameters(loaded_ndarrays)
        self.assertIsNotNone(initial_parameters)
        print("Verification successful: Checkpoint loading and key sorting work correctly.")

if __name__ == "__main__":
    unittest.main()

import os
import pickle

# Directory to save profiles
profile_dir = 'path/to/profile_directory'

if not os.path.exists(profile_dir):
    os.makedirs(profile_dir)

# Sample initial profiles structure
profiles = {
    "Person1": {"birth_year": 1980, "embeddings": [], "ages": []},
    "Person2": {"birth_year": 1975, "embeddings": [], "ages": []}
}

# Save initial profiles
with open(os.path.join(profile_dir, 'profiles.pkl'), 'wb') as f:
    pickle.dump(profiles, f)

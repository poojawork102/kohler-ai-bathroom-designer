import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# 1. Synthesize 1,200 records using native INR Budgets (₹1.5 Lakh to ₹25 Lakh)
np.random.seed(42)
n_samples = 1200
budgets_inr = np.random.uniform(150000, 2500000, n_samples)
sqft = np.random.uniform(30, 250, n_samples)
occupancy = np.random.randint(1, 7, n_samples)
eco_priority = np.random.randint(1, 6, n_samples)

# 2. Heuristic mapping based on INR
labels = []
for b, s, occ, eco in zip(budgets_inr, sqft, occupancy, eco_priority):
    # Adjust score formula for INR scale
    score = (b * 0.005) + (s * 40) + (eco * 800) + np.random.normal(0, 500)
    if score < 4500:
        labels.append(0)  # Standard
    elif score < 9500 or (eco >= 4 and b >= 350000):
        labels.append(1)  # Eco-Smart
    else:
        labels.append(2)  # Luxury Numi Series

# 3. Train the Model
X = pd.DataFrame({'budget_inr': budgets_inr, 'sqft': sqft, 'occupancy': occupancy, 'eco_priority': eco_priority})
y = np.array(labels)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
clf.fit(X_train, y_train)

# 4. Save the Model
with open('kohler_tier_model.pkl', 'wb') as f:
    pickle.dump(clf, f)
print("SUCCESS: Native INR model saved as kohler_tier_model.pkl")

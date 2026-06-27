"""Original university coursework script (preserved for provenance).

This is the single-file version BreachLens grew out of. The maintained, productised
implementation lives in the `breachlens` package — use that instead. Kept here so the
project's evolution from a class assignment into a real tool stays visible.

Run from the repo root:  python examples/original_coursework.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# 1. Load the dataset
DATA = Path(__file__).resolve().parent.parent / "data" / "cyber_breach.xlsx"
df = pd.read_excel(DATA)
print(df.head())
print("Average breach cost: Rs", round(df["breach_cost"].mean(), 2), "crore\n")

# 2. Inputs (X) and target (y)
features = ["records_exposed", "detection_time", "response_time", "security_score"]
X = df[features]
y = df["breach_cost"]

# 3. Train / test split (80 / 20)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=2
)

# 4. Simple Linear Regression (one feature: records_exposed)
simple = LinearRegression()
simple.fit(X_train[["records_exposed"]], y_train)
simple_pred = simple.predict(X_test[["records_exposed"]])
print("Simple Linear Regression (records_exposed only)")
print("  R2 :", round(r2_score(y_test, simple_pred), 3))
print("  MAE:", round(mean_absolute_error(y_test, simple_pred), 2), "crore\n")

# 5. Multiple Linear Regression (all four features)
multi = LinearRegression()
multi.fit(X_train, y_train)
multi_pred = multi.predict(X_test)
print("Multiple Linear Regression (all four features)")
print("  R2 :", round(r2_score(y_test, multi_pred), 3))
print("  MAE:", round(mean_absolute_error(y_test, multi_pred), 2), "crore")
print("  Coefficients:")
for f, c in zip(features, multi.coef_):
    print(f"    {f:16s}: {c:+.3f}")
print("  Intercept:", round(multi.intercept_, 3), "\n")

# 6. Predict the cost of a new breach
new_breach = pd.DataFrame(
    [[300, 200, 90, 40]], columns=features
)  # 300k records, 200 days detect, 90 days contain, security 40
quote = multi.predict(new_breach)[0]
print("Example prediction for a new breach:")
print("  Predicted cost: Rs", round(quote, 2), "crore\n")

# 7. Visualisation: records exposed vs breach cost with simple best-fit line
plot_model = LinearRegression().fit(X[["records_exposed"]], y)
order = X["records_exposed"].argsort()
plt.scatter(df["records_exposed"], df["breach_cost"], alpha=0.6)
plt.plot(
    df["records_exposed"].iloc[order],
    plot_model.predict(X[["records_exposed"]]).take(order),
    color="red",
)
plt.xlabel("Records Exposed (thousands)")
plt.ylabel("Breach Cost (Rs crore)")
plt.title("Data Breach Cost Prediction")
plt.tight_layout()
plt.show()

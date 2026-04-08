import pandas as pd
import numpy as np

from sklearn.linear_model import ElasticNet, LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

df = pd.read_csv(
    "/kaggle/input/datasets/amaliyadubrovskaya04/currency/cbu_currency_rates_2017-09-06_2026-03-29.csv",
    low_memory=False
)

usd = df[df["ccy"] == "USD"].copy()
usd["published_date"] = pd.to_datetime(usd["published_date"], dayfirst=True, errors="coerce")
usd["rate"] = pd.to_numeric(usd["rate"], errors="coerce")

usd = usd.dropna(subset=["published_date", "rate"])
usd = usd.sort_values("published_date")

usd = usd.groupby("published_date")["rate"].last().reset_index()

usd["lag1"] = usd["rate"].shift(1)
usd["lag2"] = usd["rate"].shift(2)

usd["day_of_week"] = usd["published_date"].dt.dayofweek
usd["month"] = usd["published_date"].dt.month
usd["day_of_month"] = usd["published_date"].dt.day

usd = usd.dropna().reset_index(drop=True)

train_size = int(len(usd) * 0.8)

train = usd.iloc[:train_size].copy()
test = usd.iloc[train_size:].copy()

feature_cols = ["lag1", "lag2", "day_of_week", "month", "day_of_month"]

X_train = train[feature_cols]
y_train = train["rate"]

X_test = test[feature_cols]
y_test = test["rate"]

baseline_pred = test["lag1"].values

lr_model = LinearRegression()
lr_model.fit(X_train, y_train)
lr_pred = lr_model.predict(X_test)

enet_model = ElasticNet(alpha=0.0001, l1_ratio=0.05, max_iter=20000)
enet_model.fit(X_train, y_train)
enet_pred = enet_model.predict(X_test)

def calc_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return mae, rmse, mape

results = []

for name, pred in [
    ("Baseline", baseline_pred),
    ("Linear Regression", lr_pred),
    ("ElasticNet", enet_pred),
]:
    mae, rmse, mape = calc_metrics(y_test, pred)
    results.append([name, mae, rmse, mape])

results_df = pd.DataFrame(results, columns=["Model", "MAE", "RMSE", "MAPE (%)"])
print(results_df.sort_values("MAE"))

# Результат
                       # Model        MAE       RMSE  MAPE (%)
# 1           Linear Regression  31.348241  39.749293  0.252336
# 2                  ElasticNet  31.348298  39.749327  0.252336
# 0                    Baseline  34.908797  42.705772  0.281162

#  Помимо этого я проверила более сложные алгориты(CatBoost, SVR, XGBoost, Prophet), которые оказались намного хуже легких моделей
# 

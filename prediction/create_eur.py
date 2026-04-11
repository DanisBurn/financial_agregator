import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error

df = pd.read_csv(
    "/kaggle/input/datasets/amaliyadubrovskaya04/currency/cbu_currency_rates_2017-09-06_2026-03-29.csv",
    low_memory=False
)

eur = df[df["ccy"] == "EUR"].copy()

eur["published_date"] = pd.to_datetime(eur["published_date"], dayfirst=True, errors="coerce")
eur["rate"] = pd.to_numeric(eur["rate"], errors="coerce")

eur = eur.dropna(subset=["published_date", "rate"])
eur = eur.sort_values("published_date")
eur = eur.groupby("published_date")["rate"].last().reset_index()

eur["lag1"] = eur["rate"].shift(1)
eur["lag2"] = eur["rate"].shift(2)

eur["diff_lag1_lag2"]     = eur["lag1"] - eur["lag2"]         
eur["ratio_lag1_lag2"]    = eur["lag1"] / eur["lag2"].replace(0, np.nan)  
eur["mean_lag1_lag2"]     = (eur["lag1"] + eur["lag2"]) / 2   

eur["day_of_week"]  = eur["published_date"].dt.dayofweek
eur["month"]        = eur["published_date"].dt.month
eur["day_of_month"] = eur["published_date"].dt.day

eur["dow_sin"]   = np.sin(2 * np.pi * eur["day_of_week"] / 7)
eur["dow_cos"]   = np.cos(2 * np.pi * eur["day_of_week"] / 7)
eur["month_sin"] = np.sin(2 * np.pi * eur["month"] / 12)
eur["month_cos"] = np.cos(2 * np.pi * eur["month"] / 12)

eur = eur.dropna().reset_index(drop=True)
FEATURE_COLS = [
    "lag1", "lag2",
    "diff_lag1_lag2",
    "ratio_lag1_lag2",
    "mean_lag1_lag2",
    "day_of_week", "month", "day_of_month",
    "dow_sin", "dow_cos",
    "month_sin", "month_cos",
]

X = eur[FEATURE_COLS]
y = eur["rate"]

def smape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom != 0
    return np.mean(2 * np.abs(y_true[mask] - y_pred[mask]) / denom[mask]) * 100

def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def evaluate(y_true, y_pred):
    return {
        "MAE":   mean_absolute_error(y_true, y_pred),
        "RMSE":  np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAPE":  mape(y_true, y_pred),
        "SMAPE": smape(y_true, y_pred),
    }

outer_cv = TimeSeriesSplit(n_splits=5)
results  = []
best_models = {}  
for fold, (train_idx, test_idx) in enumerate(outer_cv.split(X), start=1):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    # --- Baseline ---
    results.append({"model": "Baseline_lag1", "fold": fold,
                    **evaluate(y_test, X_test["lag1"].values)})

    inner_cv = TimeSeriesSplit(n_splits=3)

    # --- LinearRegression ---
    lr = Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])
    lr.fit(X_train, y_train)
    results.append({"model": "LinearRegression", "fold": fold,
                    **evaluate(y_test, lr.predict(X_test))})

    # --- Ridge ---
    ridge_search = GridSearchCV(
        Pipeline([("scaler", StandardScaler()), ("model", Ridge())]),
        {"model__alpha": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]},
        cv=inner_cv, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    ridge_search.fit(X_train, y_train)
    best_alpha_r = ridge_search.best_params_["model__alpha"]
    results.append({"model": f"Ridge_alpha={best_alpha_r}", "fold": fold,
                    **evaluate(y_test, ridge_search.best_estimator_.predict(X_test))})

    # --- Lasso ---
    lasso_search = GridSearchCV(
        Pipeline([("scaler", StandardScaler()), ("model", Lasso(max_iter=20000))]),
        {"model__alpha": [0.0001, 0.001, 0.01, 0.1, 1.0]},
        cv=inner_cv, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    lasso_search.fit(X_train, y_train)
    best_alpha_l = lasso_search.best_params_["model__alpha"]
    results.append({"model": f"Lasso_alpha={best_alpha_l}", "fold": fold,
                    **evaluate(y_test, lasso_search.best_estimator_.predict(X_test))})

    # --- ElasticNet ---
    enet_search = GridSearchCV(
        Pipeline([("scaler", StandardScaler()), ("model", ElasticNet(max_iter=20000))]),
        {"model__alpha": [0.0001, 0.001, 0.01, 0.1],
         "model__l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9]},
        cv=inner_cv, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    enet_search.fit(X_train, y_train)
    best_a = enet_search.best_params_["model__alpha"]
    best_l = enet_search.best_params_["model__l1_ratio"]
    results.append({"model": f"ElasticNet_a={best_a}_l1={best_l}", "fold": fold,
                    **evaluate(y_test, enet_search.best_estimator_.predict(X_test))})

    # Сохраняем лучшую (не baseline) модель фолда по MAE
    fold_results = [r for r in results if r["fold"] == fold and r["model"] != "Baseline_lag1"]
    best_fold    = min(fold_results, key=lambda r: r["MAE"])
    best_models[fold] = {
        "model_name": best_fold["model"],
        "MAE": best_fold["MAE"],
        "estimator": (
            lr if "LinearRegression" in best_fold["model"]
            else ridge_search.best_estimator_ if "Ridge" in best_fold["model"]
            else lasso_search.best_estimator_ if "Lasso" in best_fold["model"]
            else enet_search.best_estimator_
        )
    }

results_df = pd.DataFrame(results)
summary_df = (results_df.groupby("model")[["MAE","RMSE","MAPE","SMAPE"]]
              .mean().sort_values("MAE").reset_index())

print("=== Результаты по фолдам ===")
print(results_df.to_string(index=False))
print("\n=== Средние по фолдам ===")
print(summary_df.to_string(index=False))

results_df.to_csv("eur_lag2_results.csv", index=False)
summary_df.to_csv("eur_lag2_summary.csv",  index=False)
non_baseline = summary_df[~summary_df["model"].str.contains("Baseline")]
best_model_name = non_baseline.iloc[0]["model"]

# Переобучаем на всех данных
if "LinearRegression" in best_model_name:
    final_estimator = Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])
elif "Ridge" in best_model_name:
    alpha = float(best_model_name.split("=")[1])
    final_estimator = Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=alpha))])
elif "Lasso" in best_model_name:
    alpha = float(best_model_name.split("=")[1])
    final_estimator = Pipeline([("scaler", StandardScaler()), ("model", Lasso(alpha=alpha, max_iter=20000))])
else:
    parts = best_model_name.split("_")
    alpha = float(parts[1].split("=")[1])
    l1    = float(parts[2].split("=")[1])
    final_estimator = Pipeline([("scaler", StandardScaler()),
                                ("model", ElasticNet(alpha=alpha, l1_ratio=l1, max_iter=20000))])

final_estimator.fit(X, y)

joblib.dump(
    {"model_name": best_model_name, "model": final_estimator, "features": FEATURE_COLS},
    "best_eur_model_lag2_only.pkl"
)

print(f"\nЛучшая модель: {best_model_name}")
print(f"Сохранена в: best_eur_model_lag2_only.pkl")
print(f"Признаки: {FEATURE_COLS}")

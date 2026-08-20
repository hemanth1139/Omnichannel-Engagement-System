# Databricks notebook source
# MAGIC %pip install xgboost shap

# COMMAND ----------

#imports and configuration
import os
import glob
import warnings
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.calibration import CalibratedClassifierCV

from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

import xgboost as xgb
import shap

from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

np.random.seed(42)

print("Imports completed successfully.")

# COMMAND ----------

#load silver tables from databricks
email_df = spark.table(
    "workspace.silver.email_activity"
).toPandas()

web_df = spark.table(
    "workspace.silver.web_activity"
).toPandas()

event_df = spark.table(
    "workspace.silver.event_activity"
).toPandas()

veeva_df = spark.table(
    "workspace.silver.veeva_activity"
).toPandas()

hcp_norm_df = spark.table(
    "workspace.silver.hcp_features_normalized"
).toPandas()


print("Data loaded successfully")

print("Email:", email_df.shape)
print("Web:", web_df.shape)
print("Event:", event_df.shape)
print("Veeva:", veeva_df.shape)
print("HCP features:", hcp_norm_df.shape)

# COMMAND ----------

#timestamp and data preparation


email_df["ts"] = pd.to_datetime(email_df["event_timestamp"])
web_df["ts"] = pd.to_datetime(web_df["event_timestamp"])
event_df["ts"] = pd.to_datetime(event_df["activity_timestamp"])
veeva_df["ts"] = pd.to_datetime(veeva_df["interaction_timestamp"])

email_df["date"] = email_df["ts"].dt.date
web_df["date"] = web_df["ts"].dt.date
event_df["date"] = event_df["ts"].dt.date
veeva_df["date"] = veeva_df["ts"].dt.date

print("Timestamp and date preparation completed.")
print("Email:", email_df["ts"].min(), "→", email_df["ts"].max())
print("Web:", web_df["ts"].min(), "→", web_df["ts"].max())
print("Event:", event_df["ts"].min(), "→", event_df["ts"].max())
print("Veeva:", veeva_df["ts"].min(), "→", veeva_df["ts"].max())

# COMMAND ----------

#create channel event flags
# -------------------------
# EMAIL
# -------------------------

email_df["is_delivered"] = (
    email_df["event_type"] == "delivered"
).astype(int)

email_df["is_bounced"] = (
    email_df["event_type"] == "bounced"
).astype(int)

email_df["is_open"] = (
    email_df["event_type"] == "open"
).astype(int)

email_df["is_click"] = (
    email_df["event_type"] == "click"
).astype(int)


# -------------------------
# WEB
# -------------------------

web_df["is_pv"] = (
    web_df["event_type"] == "page_view"
).astype(int)

web_df["is_cv"] = (
    web_df["event_type"] == "content_view"
).astype(int)

web_df["is_dl"] = (
    web_df["event_type"] == "download"
).astype(int)

web_df["is_vs"] = (
    web_df["event_type"] == "video_start"
).astype(int)

web_df["is_vc"] = (
    web_df["event_type"] == "video_complete"
).astype(int)


# -------------------------
# EVENT / WEBINAR
# -------------------------

event_df["is_reg"] = (
    event_df["event_activity_type"] == "registration"
).astype(int)

event_df["is_att"] = (
    event_df["event_activity_type"] == "attendance"
).astype(int)


# -------------------------
# VEEVA
# -------------------------

veeva_df["is_comp"] = (
    veeva_df["interaction_status"] == "Completed"
).astype(int)

veeva_df["is_canc"] = (
    veeva_df["interaction_status"] == "Cancelled"
).astype(int)

veeva_df["is_ns"] = (
    veeva_df["interaction_status"] == "No Show"
).astype(int)

veeva_df["is_inperson"] = (
    veeva_df["interaction_type"] == "In-Person Visit"
).astype(int)

veeva_df["is_phone"] = (
    veeva_df["interaction_type"] == "Phone Call"
).astype(int)

veeva_df["is_virtual"] = (
    veeva_df["interaction_type"] == "Virtual Meeting"
).astype(int)

veeva_df["is_followup"] = (
    veeva_df["follow_up_required"] == "Yes"
).astype(int)


print("Channel event flags created successfully.")

# COMMAND ----------

#temporary snapshot configuration
HISTORY_DAYS = 60
FUTURE_DAYS = 30

# Use the common date range covered by the activity data
DATA_START = pd.Timestamp("2026-01-01")
DATA_END = pd.Timestamp("2026-08-15")

print("Temporal snapshot configuration")
print("---------------------------------")
print(f"History window : {HISTORY_DAYS} days")
print(f"Future window  : {FUTURE_DAYS} days")
print(f"Data start     : {DATA_START.date()}")
print(f"Data end       : {DATA_END.date()}")

# COMMAND ----------

#temporal snapshot function
# ============================================================
# CELL 6: TEMPORAL SNAPSHOT FEATURE & TARGET EXTRACTION
# ============================================================

def extract_snapshot(T, hist_days=60, fut_days=30):

    t_start = T - pd.Timedelta(days=hist_days)
    t_end = T
    t_fut_end = T + pd.Timedelta(days=fut_days)

    # --------------------------------------------------------
    # Historical windows
    # --------------------------------------------------------

    em_h = email_df[
        (email_df["ts"] >= t_start) &
        (email_df["ts"] <= t_end)
    ]

    web_h = web_df[
        (web_df["ts"] >= t_start) &
        (web_df["ts"] <= t_end)
    ]

    evt_h = event_df[
        (event_df["ts"] >= t_start) &
        (event_df["ts"] <= t_end)
    ]

    veeva_h = veeva_df[
        (veeva_df["ts"] >= t_start) &
        (veeva_df["ts"] <= t_end)
    ]

    # --------------------------------------------------------
    # Email features
    # --------------------------------------------------------

    em_g = em_h.groupby("hcp_id").agg(
        email_delivered=("is_delivered", "sum"),
        email_bounced=("is_bounced", "sum"),
        email_opens=("is_open", "sum"),
        email_clicks=("is_click", "sum"),
        email_unique_emails=("email_id", "nunique"),
        email_unique_campaigns=("campaign_id", "nunique"),
        email_unique_drugs=("drug_id", "nunique"),
        email_active_days=("date", "nunique"),
        email_last_ts=("ts", "max")
    ).reset_index()

    em_eng = (
        em_h[
            (em_h["is_open"] == 1) |
            (em_h["is_click"] == 1)
        ]
        .groupby("hcp_id")["ts"]
        .max()
        .reset_index()
        .rename(columns={"ts": "email_last_eng_ts"})
    )

    em_g = em_g.merge(
        em_eng,
        on="hcp_id",
        how="left"
    )

    em_g["email_open_rate"] = (
        em_g["email_opens"] /
        np.maximum(em_g["email_delivered"], 1)
    )

    em_g["email_click_rate"] = (
        em_g["email_clicks"] /
        np.maximum(em_g["email_delivered"], 1)
    )

    em_g["email_ctor"] = (
        em_g["email_clicks"] /
        np.maximum(em_g["email_opens"], 1)
    )

    em_g["email_recency_days"] = (
        (T - em_g["email_last_ts"])
        .dt.total_seconds() / 86400.0
    )

    em_g["email_eng_recency_days"] = (
        (T - em_g["email_last_eng_ts"])
        .dt.total_seconds() / 86400.0
    )

    em_g["email_recency_days"] = (
        em_g["email_recency_days"].fillna(hist_days)
    )

    em_g["email_eng_recency_days"] = (
        em_g["email_eng_recency_days"].fillna(hist_days)
    )

    em_g.drop(
        columns=[
            "email_last_ts",
            "email_last_eng_ts"
        ],
        inplace=True
    )

    # --------------------------------------------------------
    # Web features
    # --------------------------------------------------------

    web_g = web_h.groupby("hcp_id").agg(
        web_total_events=("web_event_id", "count"),
        web_unique_sessions=("session_id", "nunique"),
        web_page_views=("is_pv", "sum"),
        web_content_views=("is_cv", "sum"),
        web_downloads=("is_dl", "sum"),
        web_video_starts=("is_vs", "sum"),
        web_video_completes=("is_vc", "sum"),
        web_total_duration=("session_duration_seconds", "sum"),
        web_avg_duration=("session_duration_seconds", "mean"),
        web_max_duration=("session_duration_seconds", "max"),
        web_active_days=("date", "nunique"),
        web_unique_campaigns=("campaign_id", "nunique"),
        web_unique_drugs=("drug_id", "nunique"),
        web_last_ts=("ts", "max")
    ).reset_index()

    web_eng = (
        web_h[
            (web_h["is_cv"] == 1) |
            (web_h["is_dl"] == 1) |
            (web_h["is_vc"] == 1)
        ]
        .groupby("hcp_id")["ts"]
        .max()
        .reset_index()
        .rename(columns={"ts": "web_last_eng_ts"})
    )

    web_g = web_g.merge(
        web_eng,
        on="hcp_id",
        how="left"
    )

    web_g["web_video_completion_rate"] = (
        web_g["web_video_completes"] /
        np.maximum(web_g["web_video_starts"], 1)
    )

    web_g["web_recency_days"] = (
        (T - web_g["web_last_ts"])
        .dt.total_seconds() / 86400.0
    )

    web_g["web_eng_recency_days"] = (
        (T - web_g["web_last_eng_ts"])
        .dt.total_seconds() / 86400.0
    )

    web_g["web_recency_days"] = (
        web_g["web_recency_days"].fillna(hist_days)
    )

    web_g["web_eng_recency_days"] = (
        web_g["web_eng_recency_days"].fillna(hist_days)
    )

    web_g.drop(
        columns=[
            "web_last_ts",
            "web_last_eng_ts"
        ],
        inplace=True
    )

    # --------------------------------------------------------
    # Event features
    # --------------------------------------------------------

    evt_g = evt_h.groupby("hcp_id").agg(
        event_registrations=("is_reg", "sum"),
        event_attendances=("is_att", "sum"),
        event_total_duration=(
            "attendance_duration_minutes",
            "sum"
        ),
        event_avg_duration=(
            "attendance_duration_minutes",
            "mean"
        ),
        event_questions=("questions_asked", "sum"),
        event_polls=("poll_responses", "sum"),
        event_active_days=("date", "nunique"),
        event_unique_events=("event_id", "nunique"),
        event_unique_campaigns=("campaign_id", "nunique"),
        event_unique_drugs=("drug_id", "nunique"),
        event_last_ts=("ts", "max")
    ).reset_index()

    evt_eng = (
        evt_h[evt_h["is_att"] == 1]
        .groupby("hcp_id")["ts"]
        .max()
        .reset_index()
        .rename(columns={"ts": "event_last_att_ts"})
    )

    evt_g = evt_g.merge(
        evt_eng,
        on="hcp_id",
        how="left"
    )

    evt_g["event_attendance_rate"] = (
        evt_g["event_attendances"] /
        np.maximum(evt_g["event_registrations"], 1)
    )

    evt_g["event_recency_days"] = (
        (T - evt_g["event_last_ts"])
        .dt.total_seconds() / 86400.0
    )

    evt_g["event_att_recency_days"] = (
        (T - evt_g["event_last_att_ts"])
        .dt.total_seconds() / 86400.0
    )

    evt_g["event_recency_days"] = (
        evt_g["event_recency_days"].fillna(hist_days)
    )

    evt_g["event_att_recency_days"] = (
        evt_g["event_att_recency_days"].fillna(hist_days)
    )

    evt_g.drop(
        columns=[
            "event_last_ts",
            "event_last_att_ts"
        ],
        inplace=True
    )

    # --------------------------------------------------------
    # Veeva features
    # --------------------------------------------------------

    veeva_g = veeva_h.groupby("hcp_id").agg(
        veeva_total_interactions=("is_comp", "count"),
        veeva_completed=("is_comp", "sum"),
        veeva_cancelled=("is_canc", "sum"),
        veeva_no_show=("is_ns", "sum"),
        veeva_in_person=("is_inperson", "sum"),
        veeva_phone=("is_phone", "sum"),
        veeva_virtual=("is_virtual", "sum"),
        veeva_total_duration=(
            "interaction_duration_minutes",
            "sum"
        ),
        veeva_avg_duration=(
            "interaction_duration_minutes",
            "mean"
        ),
        veeva_follow_up_count=("is_followup", "sum"),
        veeva_active_days=("date", "nunique"),
        veeva_unique_reps=("rep_id", "nunique"),
        veeva_unique_campaigns=("campaign_id", "nunique"),
        veeva_unique_drugs=("drug_id", "nunique"),
        veeva_last_ts=("ts", "max")
    ).reset_index()

    veeva_eng = (
        veeva_h[veeva_h["is_comp"] == 1]
        .groupby("hcp_id")["ts"]
        .max()
        .reset_index()
        .rename(columns={"ts": "veeva_last_comp_ts"})
    )

    veeva_g = veeva_g.merge(
        veeva_eng,
        on="hcp_id",
        how="left"
    )

    veeva_g["veeva_completion_rate"] = (
        veeva_g["veeva_completed"] /
        np.maximum(
            veeva_g["veeva_total_interactions"],
            1
        )
    )

    veeva_g["veeva_recency_days"] = (
        (T - veeva_g["veeva_last_ts"])
        .dt.total_seconds() / 86400.0
    )

    veeva_g["veeva_comp_recency_days"] = (
        (T - veeva_g["veeva_last_comp_ts"])
        .dt.total_seconds() / 86400.0
    )

    veeva_g["veeva_recency_days"] = (
        veeva_g["veeva_recency_days"].fillna(hist_days)
    )

    veeva_g["veeva_comp_recency_days"] = (
        veeva_g["veeva_comp_recency_days"].fillna(hist_days)
    )

    veeva_g.drop(
        columns=[
            "veeva_last_ts",
            "veeva_last_comp_ts"
        ],
        inplace=True
    )

    # --------------------------------------------------------
    # Merge all historical features
    # --------------------------------------------------------

    df_snap = all_hcps.merge(
        em_g,
        on="hcp_id",
        how="left"
    )

    df_snap = df_snap.merge(
        web_g,
        on="hcp_id",
        how="left"
    )

    df_snap = df_snap.merge(
        evt_g,
        on="hcp_id",
        how="left"
    )

    df_snap = df_snap.merge(
        veeva_g,
        on="hcp_id",
        how="left"
    )

    # --------------------------------------------------------
    # Fill missing values
    # --------------------------------------------------------

    for c in df_snap.columns:

        if c == "hcp_id":
            continue

        if "recency" in c:
            df_snap[c] = df_snap[c].fillna(hist_days)

        else:
            df_snap[c] = df_snap[c].fillna(0)

    # --------------------------------------------------------
    # Cross-channel features
    # --------------------------------------------------------

    df_snap["total_touchpoints"] = (
        df_snap["email_delivered"] +
        df_snap["web_total_events"] +
        df_snap["event_registrations"] +
        df_snap["veeva_total_interactions"]
    )

    df_snap["active_channel_count"] = (
        (df_snap["email_delivered"] > 0).astype(int) +
        (df_snap["web_total_events"] > 0).astype(int) +
        (df_snap["event_registrations"] > 0).astype(int) +
        (df_snap["veeva_total_interactions"] > 0).astype(int)
    )

    df_snap["email_proportion"] = (
        df_snap["email_delivered"] /
        np.maximum(df_snap["total_touchpoints"], 1)
    )

    df_snap["web_proportion"] = (
        df_snap["web_total_events"] /
        np.maximum(df_snap["total_touchpoints"], 1)
    )

    df_snap["event_proportion"] = (
        df_snap["event_registrations"] /
        np.maximum(df_snap["total_touchpoints"], 1)
    )

    df_snap["veeva_proportion"] = (
        df_snap["veeva_total_interactions"] /
        np.maximum(df_snap["total_touchpoints"], 1)
    )

    df_snap["digital_touchpoints"] = (
        df_snap["email_delivered"] +
        df_snap["web_total_events"] +
        df_snap["event_registrations"]
    )

    df_snap["field_touchpoints"] = (
        df_snap["veeva_total_interactions"]
    )

    df_snap["digital_to_field_ratio"] = (
        df_snap["digital_touchpoints"] /
        np.maximum(df_snap["field_touchpoints"], 1)
    )

    df_snap["snapshot_date"] = T

    # Add your existing normalized HCP features
    df_snap = df_snap.merge(
        hcp_norm_df,
        on="hcp_id",
        how="left"
    )

    # --------------------------------------------------------
    # Future targets
    # --------------------------------------------------------

    em_f = email_df[
        (email_df["ts"] > T) &
        (email_df["ts"] <= t_fut_end)
    ]

    web_f = web_df[
        (web_df["ts"] > T) &
        (web_df["ts"] <= t_fut_end)
    ]

    evt_f = event_df[
        (event_df["ts"] > T) &
        (event_df["ts"] <= t_fut_end)
    ]

    veeva_f = veeva_df[
        (veeva_df["ts"] > T) &
        (veeva_df["ts"] <= t_fut_end)
    ]

    em_eng_hcps = set(
        em_f[
            (em_f["is_open"] == 1) |
            (em_f["is_click"] == 1)
        ]["hcp_id"].unique()
    )

    web_eng_hcps = set(
        web_f[
            (web_f["is_cv"] == 1) |
            (web_f["is_dl"] == 1) |
            (web_f["is_vc"] == 1)
        ]["hcp_id"].unique()
    )

    evt_eng_hcps = set(
        evt_f[
            evt_f["is_att"] == 1
        ]["hcp_id"].unique()
    )

    veeva_eng_hcps = set(
        veeva_f[
            veeva_f["is_comp"] == 1
        ]["hcp_id"].unique()
    )

    df_snap["email_target"] = (
        df_snap["hcp_id"]
        .isin(em_eng_hcps)
        .astype(int)
    )

    df_snap["web_target"] = (
        df_snap["hcp_id"]
        .isin(web_eng_hcps)
        .astype(int)
    )

    df_snap["webinar_target"] = (
        df_snap["hcp_id"]
        .isin(evt_eng_hcps)
        .astype(int)
    )

    df_snap["veeva_target"] = (
        df_snap["hcp_id"]
        .isin(veeva_eng_hcps)
        .astype(int)
    )

    return df_snap


print("extract_snapshot function created successfully.")

# COMMAND ----------

#hcp list
all_hcps = pd.DataFrame({
    "hcp_id": hcp_norm_df["hcp_id"].dropna().unique()
})

print("Total HCPs:", len(all_hcps))

# COMMAND ----------

# ============================================================
# CELL 7: CHRONOLOGICAL DATASET CONSTRUCTION
# ============================================================

train_dates = [
    pd.Timestamp("2026-03-02"),
    pd.Timestamp("2026-03-16"),
    pd.Timestamp("2026-04-01"),
    pd.Timestamp("2026-04-16"),
    pd.Timestamp("2026-05-01")
]

val_dates = [
    pd.Timestamp("2026-05-16"),
    pd.Timestamp("2026-06-01")
]

test_dates = [
    pd.Timestamp("2026-06-16"),
    pd.Timestamp("2026-07-01")
]

curr_date = pd.Timestamp("2026-08-15")


print("Building training snapshots...")

train_df = pd.concat(
    [extract_snapshot(d) for d in train_dates],
    ignore_index=True
)

print("Building validation snapshots...")

val_df = pd.concat(
    [extract_snapshot(d) for d in val_dates],
    ignore_index=True
)

print("Building test snapshots...")

test_df = pd.concat(
    [extract_snapshot(d) for d in test_dates],
    ignore_index=True
)

print("Building current HCP snapshot...")

curr_df = extract_snapshot(curr_date)


# ------------------------------------------------------------
# Feature selection
# ------------------------------------------------------------

exclude_cols = {
    "hcp_id",
    "snapshot_date",
    "email_target",
    "web_target",
    "webinar_target",
    "veeva_target"
}

feature_cols = [
    c for c in train_df.columns
    if c not in exclude_cols
]


X_train = train_df[feature_cols].copy()
X_val = val_df[feature_cols].copy()
X_test = test_df[feature_cols].copy()
X_curr = curr_df[feature_cols].copy()


print("\nChronological dataset construction completed.")
print("---------------------------------------------")
print("Training shape   :", train_df.shape)
print("Validation shape :", val_df.shape)
print("Test shape       :", test_df.shape)
print("Current HCP shape:", curr_df.shape)
print("Number of features:", len(feature_cols))

# COMMAND ----------

# ============================================================
# CELL 8: HISTORICAL ENGAGEMENT SCORE VIA PCA
# ============================================================

scaler_pca = StandardScaler()

X_train_scaled = scaler_pca.fit_transform(X_train)

X_val_scaled = scaler_pca.transform(X_val)

X_test_scaled = scaler_pca.transform(X_test)

X_curr_scaled = scaler_pca.transform(X_curr)


# ------------------------------------------------------------
# Fit PCA ONLY on training data
# ------------------------------------------------------------

pca = PCA(
    n_components=1,
    random_state=42
)

pc1_train = pca.fit_transform(
    X_train_scaled
)[:, 0]


# ------------------------------------------------------------
# Orient PCA score so higher = more engagement
# ------------------------------------------------------------

tp_train = train_df[
    "total_touchpoints"
].values

pca_sign = (
    -1.0
    if np.corrcoef(
        pc1_train,
        tp_train
    )[0, 1] < 0
    else 1.0
)

pc1_train_oriented = (
    pc1_train * pca_sign
)


# ------------------------------------------------------------
# Scale PCA score to 0–100
# ------------------------------------------------------------

pc1_min = pc1_train_oriented.min()

pc1_max = pc1_train_oriented.max()


def scale_pca(X_scaled):

    pc1 = (
        pca.transform(X_scaled)[:, 0]
        * pca_sign
    )

    score = (
        (pc1 - pc1_min)
        / (pc1_max - pc1_min)
        * 100.0
    )

    return np.clip(
        score,
        0.0,
        100.0
    )


# ------------------------------------------------------------
# Generate PCA scores
# ------------------------------------------------------------

hist_train_score = scale_pca(
    X_train_scaled
)

hist_val_score = scale_pca(
    X_val_scaled
)

hist_test_score = scale_pca(
    X_test_scaled
)

hist_curr_score = scale_pca(
    X_curr_scaled
)


print("PCA historical engagement score created successfully.")

print("\nExplained variance ratio:")
print(pca.explained_variance_ratio_)

print("\nTraining PCA score:")
print(
    "Min:", round(hist_train_score.min(), 2),
    "Max:", round(hist_train_score.max(), 2),
    "Mean:", round(hist_train_score.mean(), 2)
)

print("\nValidation PCA score:")
print(
    "Min:", round(hist_val_score.min(), 2),
    "Max:", round(hist_val_score.max(), 2),
    "Mean:", round(hist_val_score.mean(), 2)
)

print("\nTest PCA score:")
print(
    "Min:", round(hist_test_score.min(), 2),
    "Max:", round(hist_test_score.max(), 2),
    "Mean:", round(hist_test_score.mean(), 2)
)

print("\nCurrent PCA score:")
print(
    "Min:", round(hist_curr_score.min(), 2),
    "Max:", round(hist_curr_score.max(), 2),
    "Mean:", round(hist_curr_score.mean(), 2)
)

# COMMAND ----------

# ============================================================
# CELL 9A: CONVERT ML FEATURES TO NUMERIC
# ============================================================

# Convert all feature columns to numeric
# This does NOT change the ML methodology or feature values.

for df in [X_train, X_val, X_test, X_curr]:
    for col in feature_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

# Replace any conversion-generated NaN values
# with 0, consistent with the existing preprocessing.
X_train[feature_cols] = X_train[feature_cols].fillna(0)
X_val[feature_cols] = X_val[feature_cols].fillna(0)
X_test[feature_cols] = X_test[feature_cols].fillna(0)
X_curr[feature_cols] = X_curr[feature_cols].fillna(0)


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

non_numeric = X_train[
    feature_cols
].select_dtypes(
    exclude=["number", "bool"]
).columns.tolist()

print("Numeric conversion completed.")

print(
    "Remaining non-numeric columns:",
    len(non_numeric)
)

if non_numeric:
    print(non_numeric)
else:
    print("All ML features are numeric.")


print("\nFeature matrix shapes:")
print("Train:", X_train.shape)
print("Val  :", X_val.shape)
print("Test :", X_test.shape)
print("Curr :", X_curr.shape)

# COMMAND ----------

# ============================================================
# CELL 9: MULTI-CHANNEL XGBOOST MODELS
# ============================================================

targets = [
    "email_target",
    "web_target",
    "webinar_target",
    "veeva_target"
]

models = {}
calibrators = {}
metrics_list = []


# Handle scikit-learn version differences
try:
    from sklearn.frozen import FrozenEstimator
    use_frozen = True
except ImportError:
    use_frozen = False


for t in targets:

    print(f"\nTraining model for: {t}")

    y_tr = train_df[t].values
    y_va = val_df[t].values
    y_te = test_df[t].values

    # Handle class imbalance
    pos_weight = (
        (len(y_tr) - sum(y_tr))
        / max(sum(y_tr), 1)
    )

    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        random_state=42,
        eval_metric="logloss"
    )

    # --------------------------------------------------------
    # Train XGBoost
    # --------------------------------------------------------

    clf.fit(
        X_train,
        y_tr
    )

    # --------------------------------------------------------
    # Probability calibration
    # --------------------------------------------------------

    if use_frozen:

        cal_clf = CalibratedClassifierCV(
            estimator=FrozenEstimator(clf),
            method="sigmoid"
        )

    else:

        cal_clf = CalibratedClassifierCV(
            estimator=clf,
            method="sigmoid",
            cv="prefit"
        )

    cal_clf.fit(
        X_val,
        y_va
    )

    models[t] = clf
    calibrators[t] = cal_clf

    # --------------------------------------------------------
    # Final test predictions
    # --------------------------------------------------------

    test_probs = (
        cal_clf
        .predict_proba(X_test)[:, 1]
    )

    channel_name = (
        t
        .replace("_target", "")
        .capitalize()
    )

    if channel_name == "Web":
        channel_name = "Website"

    preds = (
        test_probs >= 0.5
    ).astype(int)

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    roc = roc_auc_score(
        y_te,
        test_probs
    )

    pr_p, pr_r, _ = precision_recall_curve(
        y_te,
        test_probs
    )

    pr_auc = auc(
        pr_r,
        pr_p
    )

    acc = accuracy_score(
        y_te,
        preds
    )

    prec = precision_score(
        y_te,
        preds,
        zero_division=0
    )

    rec = recall_score(
        y_te,
        preds,
        zero_division=0
    )

    f1 = f1_score(
        y_te,
        preds,
        zero_division=0
    )

    metrics_list.append({
        "Channel": channel_name,
        "ROC_AUC": round(roc, 4),
        "PR_AUC": round(pr_auc, 4),
        "Accuracy": round(acc, 4),
        "Precision": round(prec, 4),
        "Recall": round(rec, 4),
        "F1": round(f1, 4)
    })


# ------------------------------------------------------------
# Metrics dataframe
# ------------------------------------------------------------

metrics_df = pd.DataFrame(
    metrics_list
)


# ------------------------------------------------------------
# Overall macro-average
# ------------------------------------------------------------

overall_metrics = {
    "Channel": "Overall",

    "ROC_AUC": round(
        metrics_df["ROC_AUC"].mean(),
        4
    ),

    "PR_AUC": round(
        metrics_df["PR_AUC"].mean(),
        4
    ),

    "Accuracy": round(
        metrics_df["Accuracy"].mean(),
        4
    ),

    "Precision": round(
        metrics_df["Precision"].mean(),
        4
    ),

    "Recall": round(
        metrics_df["Recall"].mean(),
        4
    ),

    "F1": round(
        metrics_df["F1"].mean(),
        4
    )
}


metrics_df = pd.concat(
    [
        metrics_df,
        pd.DataFrame([overall_metrics])
    ],
    ignore_index=True
)


print("\n==========================================")
print("MODEL TRAINING COMPLETED")
print("==========================================")

display(metrics_df)

# COMMAND ----------

# ============================================================
# CELL 10: VALIDATION PREDICTIONS
# ============================================================

val_probs = {}

for t in targets:

    val_probs[t] = (
        calibrators[t]
        .predict_proba(X_val)[:, 1]
    )

    print(
        f"{t}: "
        f"min={val_probs[t].min():.4f}, "
        f"max={val_probs[t].max():.4f}, "
        f"mean={val_probs[t].mean():.4f}"
    )


print("\nValidation predictions generated successfully.")

# COMMAND ----------

# ============================================================
# CELL 11: VALIDATION WEIGHT OPTIMIZATION
# ============================================================

from scipy.optimize import minimize


# ------------------------------------------------------------
# Validation targets
# ------------------------------------------------------------

y_val_channels = np.column_stack([
    val_df["email_target"].values,
    val_df["web_target"].values,
    val_df["webinar_target"].values,
    val_df["veeva_target"].values
])


# ------------------------------------------------------------
# Validation channel probabilities
# ------------------------------------------------------------

P_val = np.column_stack([
    val_probs["email_target"],
    val_probs["web_target"],
    val_probs["webinar_target"],
    val_probs["veeva_target"]
])


# ------------------------------------------------------------
# Optimize channel weights
# ------------------------------------------------------------

def objective(weights):

    combined_score = (
        P_val @ weights
    )

    # We want the combined score to represent
    # future engagement across all channels.
    actual_engagement = (
        y_val_channels.mean(axis=1)
    )

    return np.mean(
        (combined_score - actual_engagement) ** 2
    )


initial_weights = np.array([
    0.25,
    0.25,
    0.25,
    0.25
])


constraints = [
    {
        "type": "eq",
        "fun": lambda w: np.sum(w) - 1.0
    }
]


bounds = [
    (0.0, 1.0),
    (0.0, 1.0),
    (0.0, 1.0),
    (0.0, 1.0)
]


result = minimize(
    objective,
    initial_weights,
    method="SLSQP",
    bounds=bounds,
    constraints=constraints
)


optimized_weights = result.x


# ------------------------------------------------------------
# Display weights
# ------------------------------------------------------------

weight_df = pd.DataFrame({
    "Channel": [
        "Email",
        "Web",
        "Webinar",
        "Veeva"
    ],
    "Weight": optimized_weights
})

weight_df["Weight_Percent"] = (
    weight_df["Weight"] * 100
)

print("Weight optimization completed.")

display(weight_df)

print(
    "\nWeights sum:",
    optimized_weights.sum()
)

# COMMAND ----------

# ============================================================
# CELL 12: VALIDATION HYBRID ENGAGEMENT SCORE
# ============================================================

# Channel probability component
val_channel_score = (
    P_val @ optimized_weights
)

# Combine historical PCA score with predicted
# future engagement probability
val_hybrid_score = (
    0.5 * hist_val_score +
    0.5 * (val_channel_score * 100.0)
)


print("Validation hybrid engagement score created.")

print(
    "Min   :",
    round(val_hybrid_score.min(), 2)
)

print(
    "Max   :",
    round(val_hybrid_score.max(), 2)
)

print(
    "Mean  :",
    round(val_hybrid_score.mean(), 2)
)

# COMMAND ----------

# ============================================================
# CELL 11: VALIDATION WEIGHT OPTIMIZATION & QUANTILE THRESHOLDING
# ============================================================

val_p_email = calibrators['email_target'].predict_proba(X_val)[:, 1]
val_p_web = calibrators['web_target'].predict_proba(X_val)[:, 1]
val_p_webinar = calibrators['webinar_target'].predict_proba(X_val)[:, 1]
val_p_veeva = calibrators['veeva_target'].predict_proba(X_val)[:, 1]


# ------------------------------------------------------------
# Fixed domain weights based on Commercial Value Hierarchy
# Sales Rep (Veeva) -> 40%
# Event/Webinar       -> 30%
# Web                 -> 20%
# Email               -> 10%
# ------------------------------------------------------------

w_vv = 0.40
w_wn = 0.30
w_wb = 0.20
w_em = 0.10


val_pred_score = (
    val_p_email * w_em +
    val_p_web * w_wb +
    val_p_webinar * w_wn +
    val_p_veeva * w_vv
) * 100.0


# ------------------------------------------------------------
# Fixed reference baseline rates
# ------------------------------------------------------------

val_prob_matrix = np.column_stack([
    val_p_email,
    val_p_web,
    val_p_webinar,
    val_p_veeva
])

channel_base_rates = val_prob_matrix.mean(axis=0)


# ------------------------------------------------------------
# Future engagement reference
# ------------------------------------------------------------

val_fut_ref = (
    val_df['email_target'].values +
    val_df['web_target'].values +
    val_df['webinar_target'].values +
    val_df['veeva_target'].values
)


# ------------------------------------------------------------
# Candidate historical/predicted hybrid weights
# ------------------------------------------------------------

candidate_hybrid_weights = [
    (0.2, 0.8),
    (0.3, 0.7),
    (0.4, 0.6),
    (0.5, 0.5),
    (0.6, 0.4),
    (0.7, 0.3),
    (0.8, 0.2)
]


best_hybrid_weights = None
best_hybrid_corr = -1.0


# ------------------------------------------------------------
# Select hybrid weights using Spearman correlation
# ------------------------------------------------------------

for hw in candidate_hybrid_weights:

    hyb = (
        hist_val_score * hw[0] +
        val_pred_score * hw[1]
    )

    corr, _ = spearmanr(
        hyb,
        val_fut_ref
    )

    if corr > best_hybrid_corr:
        best_hybrid_corr = corr
        best_hybrid_weights = hw


# ------------------------------------------------------------
# Final selected hybrid weights
# ------------------------------------------------------------

w_hist, w_pred = best_hybrid_weights


val_hybrid_score = (
    hist_val_score * w_hist +
    val_pred_score * w_pred
)


# ------------------------------------------------------------
# Quantile thresholds
# ------------------------------------------------------------

q33 = np.percentile(
    val_hybrid_score,
    33.33
)

q66 = np.percentile(
    val_hybrid_score,
    66.67
)


# ------------------------------------------------------------
# Display results
# ------------------------------------------------------------

print("Validation weight optimization completed.")
print("---------------------------------------------")

print(
    f"Veeva / Sales Rep weight : {w_vv * 100:.0f}%"
)

print(
    f"Webinar / Event weight   : {w_wn * 100:.0f}%"
)

print(
    f"Web weight               : {w_wb * 100:.0f}%"
)

print(
    f"Email weight             : {w_em * 100:.0f}%"
)

print("\nOptimized hybrid weights:")
print(
    f"Historical PCA : {w_hist * 100:.0f}%"
)

print(
    f"Predicted      : {w_pred * 100:.0f}%"
)

print(
    f"\nBest Spearman correlation: "
    f"{best_hybrid_corr:.4f}"
)

print("\nEngagement thresholds:")
print(
    f"Low / Medium threshold : {q33:.2f}"
)

print(
    f"Medium / High threshold: {q66:.2f}"
)

print("\nValidation hybrid score:")
print(
    f"Min  : {val_hybrid_score.min():.2f}"
)

print(
    f"Max  : {val_hybrid_score.max():.2f}"
)

print(
    f"Mean : {val_hybrid_score.mean():.2f}"
)

# COMMAND ----------

# ============================================================
# CELL 12: CURRENT HCP PREDICTIONS
# ============================================================

curr_p_email = (
    calibrators["email_target"]
    .predict_proba(X_curr)[:, 1]
)

curr_p_web = (
    calibrators["web_target"]
    .predict_proba(X_curr)[:, 1]
)

curr_p_webinar = (
    calibrators["webinar_target"]
    .predict_proba(X_curr)[:, 1]
)

curr_p_veeva = (
    calibrators["veeva_target"]
    .predict_proba(X_curr)[:, 1]
)


# ------------------------------------------------------------
# Channel-weighted predicted engagement
# ------------------------------------------------------------

curr_pred_score = (
    curr_p_email * w_em +
    curr_p_web * w_wb +
    curr_p_webinar * w_wn +
    curr_p_veeva * w_vv
) * 100.0


# ------------------------------------------------------------
# Final hybrid engagement score
# ------------------------------------------------------------

curr_hybrid_score = (
    hist_curr_score * w_hist +
    curr_pred_score * w_pred
)


# ------------------------------------------------------------
# Create current HCP prediction dataframe
# ------------------------------------------------------------

current_predictions = pd.DataFrame({
    "hcp_id": curr_df["hcp_id"].values,

    "historical_pca_score":
        hist_curr_score,

    "email_probability":
        curr_p_email,

    "web_probability":
        curr_p_web,

    "webinar_probability":
        curr_p_webinar,

    "veeva_probability":
        curr_p_veeva,

    "predicted_engagement_score":
        curr_pred_score,

    "overall_engagement_score":
        curr_hybrid_score
})


# ------------------------------------------------------------
# Engagement level
# ------------------------------------------------------------

current_predictions["engagement_level"] = np.select(
    [
        current_predictions["overall_engagement_score"] < q33,
        current_predictions["overall_engagement_score"] <= q66
    ],
    [
        "Low",
        "Medium"
    ],
    default="High"
)


print("Current HCP predictions generated successfully.")

print("\nCurrent prediction shape:")
print(current_predictions.shape)

print("\nEngagement level distribution:")
print(
    current_predictions[
        "engagement_level"
    ].value_counts()
)

print("\nScore statistics:")

print(
    "Min  :",
    round(
        current_predictions[
            "overall_engagement_score"
        ].min(),
        2
    )
)

print(
    "Max  :",
    round(
        current_predictions[
            "overall_engagement_score"
        ].max(),
        2
    )
)

print(
    "Mean :",
    round(
        current_predictions[
            "overall_engagement_score"
        ].mean(),
        2
    )
)

display(
    current_predictions.head(10)
)

# COMMAND ----------

# ============================================================
# CELL 13: SHAP FEATURE IMPORTANCE
# ============================================================

# Use the Veeva model as the primary explainability model
# because Veeva has the highest commercial channel weight.

veeva_model = models["veeva_target"]

# SHAP TreeExplainer
explainer = shap.TreeExplainer(
    veeva_model
)

# Explain current HCP predictions
shap_values = explainer.shap_values(
    X_curr
)

# Convert SHAP values into a dataframe
shap_df = pd.DataFrame(
    shap_values,
    columns=feature_cols
)

# Mean absolute SHAP importance
shap_importance = (
    shap_df.abs()
    .mean()
    .sort_values(ascending=False)
)

shap_importance_df = (
    shap_importance
    .reset_index()
)

shap_importance_df.columns = [
    "feature",
    "mean_abs_shap"
]

print("SHAP analysis completed.")

print("\nTop 20 features:")
display(
    shap_importance_df.head(20)
)

# COMMAND ----------

# ============================================================
# CELL 14: NEXT BEST CHANNEL + HCP-LEVEL EXPLANATIONS
# ============================================================

# Current channel probabilities
curr_p_email = calibrators['email_target'].predict_proba(X_curr)[:, 1]
curr_p_web = calibrators['web_target'].predict_proba(X_curr)[:, 1]
curr_p_webinar = calibrators['webinar_target'].predict_proba(X_curr)[:, 1]
curr_p_veeva = calibrators['veeva_target'].predict_proba(X_curr)[:, 1]


# ------------------------------------------------------------
# Predicted engagement score
# ------------------------------------------------------------

curr_pred_score = (
    curr_p_email * w_em +
    curr_p_web * w_wb +
    curr_p_webinar * w_wn +
    curr_p_veeva * w_vv
) * 100.0


# ------------------------------------------------------------
# Hybrid score
# ------------------------------------------------------------

curr_hybrid_score = (
    hist_curr_score * w_hist +
    curr_pred_score * w_pred
)


# ------------------------------------------------------------
# Engagement level
# ------------------------------------------------------------

def get_eng_level(score):

    if score <= q33:
        return 'Low'

    elif score <= q66:
        return 'Medium'

    else:
        return 'High'


eng_levels = [
    get_eng_level(s)
    for s in curr_hybrid_score
]


# ------------------------------------------------------------
# Channel probabilities
# ------------------------------------------------------------

prob_matrix = np.column_stack([
    curr_p_email,
    curr_p_web,
    curr_p_webinar,
    curr_p_veeva
])


# ------------------------------------------------------------
# Lift over baseline
# ------------------------------------------------------------

lift_matrix = (
    prob_matrix /
    np.maximum(channel_base_rates, 1e-6)
)


# ------------------------------------------------------------
# Next Best Channel
# ------------------------------------------------------------

channel_names = [
    'Email',
    'Website',
    'Webinar',
    'Sales Rep'
]

nbc_indices = np.argmax(
    lift_matrix,
    axis=1
)

nbc_list = [
    channel_names[i]
    for i in nbc_indices
]


# ------------------------------------------------------------
# SHAP explainers
# ------------------------------------------------------------

explainers = {
    'email_target':
        shap.TreeExplainer(
            models['email_target']
        ),

    'web_target':
        shap.TreeExplainer(
            models['web_target']
        ),

    'webinar_target':
        shap.TreeExplainer(
            models['webinar_target']
        ),

    'veeva_target':
        shap.TreeExplainer(
            models['veeva_target']
        )
}


# ------------------------------------------------------------
# SHAP values for all four channels
# ------------------------------------------------------------

shap_values_dict = {

    'Email':
        explainers['email_target']
        .shap_values(X_curr),

    'Website':
        explainers['web_target']
        .shap_values(X_curr),

    'Webinar':
        explainers['webinar_target']
        .shap_values(X_curr),

    'Sales Rep':
        explainers['veeva_target']
        .shap_values(X_curr)
}


# ------------------------------------------------------------
# Human-readable feature names
# ------------------------------------------------------------

feature_readable_names = {

    # Email
    'email_delivered':
        'historical email volume',

    'email_opens':
        'email open frequency',

    'email_clicks':
        'email click engagement',

    'email_open_rate':
        'email open rate',

    'email_click_rate':
        'email click rate',

    'email_ctor':
        'click-to-open rate',

    'email_recency_days':
        'email recency',

    'email_eng_recency_days':
        'email engagement recency',

    # Web
    'web_total_events':
        'website activity volume',

    'web_unique_sessions':
        'unique website sessions',

    'web_page_views':
        'web page views',

    'web_content_views':
        'web content viewing frequency',

    'web_downloads':
        'web resource download activity',

    'web_download_rate':
        'web download rate',

    'web_video_starts':
        'video starts',

    'web_video_completes':
        'video completions',

    'web_video_completion_rate':
        'video completion rate',

    'web_avg_duration':
        'average website session duration',

    'web_recency_days':
        'website recency',

    'web_eng_recency_days':
        'website engagement recency',

    # Event
    'event_registrations':
        'event registration history',

    'event_attendances':
        'event attendance history',

    'event_total_duration':
        'total event attendance duration',

    'event_avg_duration':
        'average event duration',

    'event_questions':
        'event questions asked',

    'event_polls':
        'event poll participation',

    'event_attendance_rate':
        'event attendance rate',

    'event_recency_days':
        'event registration recency',

    'event_att_recency_days':
        'event attendance recency',

    # Veeva / Sales Rep
    'veeva_total_interactions':
        'field representative interaction volume',

    'veeva_completed':
        'completed rep visits',

    'veeva_cancelled':
        'cancelled rep visits',

    'veeva_no_show':
        'rep visit no-shows',

    'veeva_in_person':
        'in-person meeting frequency',

    'veeva_phone':
        'phone meeting frequency',

    'veeva_virtual':
        'virtual meeting frequency',

    'veeva_total_duration':
        'total time spent with reps',

    'veeva_avg_duration':
        'average rep meeting duration',

    'veeva_active_days':
        'days meeting with reps',

    'veeva_unique_reps':
        'unique field reps met',

    'veeva_completion_rate':
        'rep visit completion rate',

    'veeva_recency_days':
        'sales rep interaction recency',

    'veeva_comp_recency_days':
        'completed rep visit recency',

    # Cross-channel
    'total_touchpoints':
        'cross-channel engagement volume',

    'digital_touchpoints':
        'digital engagement volume',

    'field_touchpoints':
        'field engagement volume',

    'email_proportion':
        'preference for email',

    'web_proportion':
        'preference for website',

    'event_proportion':
        'preference for events',

    'veeva_proportion':
        'preference for sales reps',

    'digital_to_field_ratio':
        'digital vs field preference',

    'active_channel_count':
        'multichannel responsiveness'
}


# ------------------------------------------------------------
# Generate HCP-level reasons
# ------------------------------------------------------------

reasons = []


for i in range(len(curr_df)):

    nbc = nbc_list[i]

    prob = prob_matrix[
        i,
        nbc_indices[i]
    ]

    sv = shap_values_dict[
        nbc
    ][i]


    # Top positive SHAP features
    top_indices = np.argsort(
        sv
    )[::-1]

    top_pos_indices = [
        idx
        for idx in top_indices
        if sv[idx] > 0
    ][:2]


    top_feat_names = []


    for idx in top_pos_indices:

        code = feature_cols[idx]

        clean_code = code.replace(
            'norm_',
            ''
        )

        name = feature_readable_names.get(
            clean_code,
            clean_code.replace('_', ' ')
        )

        top_feat_names.append(name)


    if not top_feat_names:

        code = (
            feature_cols[
                top_indices[0]
            ]
            .replace('norm_', '')
        )

        name = feature_readable_names.get(
            code,
            code.replace('_', ' ')
        )

        top_feat_names.append(name)


    feat_text = (
        " and ".join(top_feat_names)
        if len(top_feat_names) > 1
        else top_feat_names[0]
    )


    level = eng_levels[i]


    # Dynamic recommendation explanation
    if level == 'High':

        reason = (
            f"Since this HCP is highly engaged overall, "
            f"{nbc} is the ideal next step "
            f"({prob * 100:.1f}% likelihood), "
            f"driven largely by their {feat_text}."
        )

    elif level == 'Medium':

        reason = (
            f"We recommend reaching out via "
            f"{nbc} ({prob * 100:.1f}% likelihood). "
            f"The model selected this channel primarily "
            f"due to the HCP's {feat_text}."
        )

    else:

        reason = (
            f"To build momentum with this "
            f"lower-engagement HCP, {nbc} is the safest "
            f"bet ({prob * 100:.1f}% likelihood), "
            f"which strongly aligns with their {feat_text}."
        )


    reasons.append(reason)


# ------------------------------------------------------------
# FINAL ML OUTPUT
# ------------------------------------------------------------

final_predictions_df = pd.DataFrame({

    'HCP_ID':
        curr_df['hcp_id'],

    'Historical_Engagement_Score':
        np.round(
            hist_curr_score,
            2
        ),

    'Predicted_Engagement_Score':
        np.round(
            curr_pred_score,
            2
        ),

    'Hybrid_Engagement_Score':
        np.round(
            curr_hybrid_score,
            2
        ),

    'Engagement_Level':
        eng_levels,

    'Email_Probability':
        np.round(
            curr_p_email,
            4
        ),

    'Website_Probability':
        np.round(
            curr_p_web,
            4
        ),

    'Webinar_Probability':
        np.round(
            curr_p_webinar,
            4
        ),

    'Sales_Rep_Probability':
        np.round(
            curr_p_veeva,
            4
        ),

    'Next_Best_Channel':
        nbc_list,

    'Recommended_Reason':
        reasons
})


print(
    "Next Best Channel and explanations generated successfully."
)

print(
    "\nFinal output shape:",
    final_predictions_df.shape
)

print(
    "\nNext Best Channel distribution:"
)

print(
    final_predictions_df[
        'Next_Best_Channel'
    ].value_counts()
)

display(
    final_predictions_df.head(10)
)

# COMMAND ----------

# ============================================================
# CELL 15: WRITE ML OUTPUT TO GOLD
# ============================================================

ML_GOLD_TABLE = "workspace.gold.hcp_ml_engagement_scores"


# Convert pandas → Spark
ml_gold_df = spark.createDataFrame(
    final_predictions_df
)


# Write as Delta table
(
    ml_gold_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(ML_GOLD_TABLE)
)


print("ML Gold table created successfully.")
print("Table:", ML_GOLD_TABLE)
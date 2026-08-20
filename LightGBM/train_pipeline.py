import os
import warnings
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from scipy.stats import spearmanr
import shap

warnings.filterwarnings("ignore")

DATA_DIR = "Dataset" if os.path.exists("Dataset") else "new_data"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Load Data
email = pd.read_csv(os.path.join(DATA_DIR, "email_activity.csv"))
web = pd.read_csv(os.path.join(DATA_DIR, "web_activity.csv"))
evt = pd.read_csv(os.path.join(DATA_DIR, "event_activity.csv"))
veeva = pd.read_csv(os.path.join(DATA_DIR, "veeva_activity.csv"))
norm = pd.read_csv(os.path.join(DATA_DIR, "hcp_features_normalized.csv"))

# Datetime conversion
email["ts"] = pd.to_datetime(email["event_timestamp"])
web["ts"] = pd.to_datetime(web["event_timestamp"])
evt["ts"] = pd.to_datetime(evt["activity_timestamp"])
veeva["ts"] = pd.to_datetime(veeva["interaction_timestamp"])

email["date"] = email["ts"].dt.date
web["date"] = web["ts"].dt.date
evt["date"] = evt["ts"].dt.date
veeva["date"] = veeva["ts"].dt.date


# 2. Snapshot Feature Builder
def build_snapshot_dataset(T, lookback_days=60):
    hist_start = T - pd.Timedelta(days=lookback_days)
    df = pd.DataFrame({"hcp_id": [f"HCP{i:04d}" for i in range(1, 2001)]})

    # Email features
    e = email[(email["ts"] >= hist_start) & (email["ts"] < T)]
    if not e.empty:
        e_agg = (
            e.groupby("hcp_id")
            .agg(
                email_delivered=(
                    "delivery_status",
                    lambda x: (x == "Delivered").sum(),
                ),
                email_bounced=(
                    "delivery_status",
                    lambda x: (x == "Bounced").sum(),
                ),
                email_open=("event_type", lambda x: (x == "open").sum()),
                email_click=("event_type", lambda x: (x == "click").sum()),
                email_unique_emails=("email_id", "nunique"),
                email_unique_campaigns=("campaign_id", "nunique"),
                email_unique_drugs=("drug_id", "nunique"),
                email_active_days=("date", "nunique"),
                last_email_ts=("ts", "max"),
            )
            .reset_index()
        )
        e_eng = (
            e[e["event_type"].isin(["open", "click"])]
            .groupby("hcp_id")["ts"]
            .max()
            .reset_index()
            .rename(columns={"ts": "last_email_eng_ts"})
        )
        e_agg = e_agg.merge(e_eng, on="hcp_id", how="left")
    else:
        e_agg = pd.DataFrame(
            columns=[
                "hcp_id",
                "email_delivered",
                "email_bounced",
                "email_open",
                "email_click",
                "email_unique_emails",
                "email_unique_campaigns",
                "email_unique_drugs",
                "email_active_days",
                "last_email_ts",
                "last_email_eng_ts",
            ]
        )

    df = df.merge(e_agg, on="hcp_id", how="left")
    df["email_recency"] = (
        (T - df["last_email_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df["email_eng_recency"] = (
        (T - df["last_email_eng_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df.drop(columns=["last_email_ts", "last_email_eng_ts"], inplace=True)

    # Web features
    w = web[(web["ts"] >= hist_start) & (web["ts"] < T)]
    if not w.empty:
        w_agg = (
            w.groupby("hcp_id")
            .agg(
                web_total_events=("web_event_id", "count"),
                web_unique_sessions=("session_id", "nunique"),
                web_page_views=(
                    "event_type",
                    lambda x: (x == "page_view").sum(),
                ),
                web_content_views=(
                    "event_type",
                    lambda x: (x == "content_view").sum(),
                ),
                web_downloads=(
                    "event_type",
                    lambda x: (x == "download").sum(),
                ),
                web_video_starts=(
                    "event_type",
                    lambda x: (x == "video_start").sum(),
                ),
                web_video_completes=(
                    "event_type",
                    lambda x: (x == "video_complete").sum(),
                ),
                web_total_session_duration=("session_duration_seconds", "sum"),
                web_avg_session_duration=("session_duration_seconds", "mean"),
                web_max_session_duration=("session_duration_seconds", "max"),
                web_active_days=("date", "nunique"),
                web_content_type_diversity=("content_type", "nunique"),
                web_device_diversity=("device_type", "nunique"),
                last_web_ts=("ts", "max"),
            )
            .reset_index()
        )
        w_eng = (
            w[
                w["event_type"].isin(
                    [
                        "content_view",
                        "download",
                        "video_start",
                        "video_complete",
                    ]
                )
            ]
            .groupby("hcp_id")["ts"]
            .max()
            .reset_index()
            .rename(columns={"ts": "last_web_eng_ts"})
        )
        w_agg = w_agg.merge(w_eng, on="hcp_id", how="left")
    else:
        w_agg = pd.DataFrame(
            columns=[
                "hcp_id",
                "web_total_events",
                "web_unique_sessions",
                "web_page_views",
                "web_content_views",
                "web_downloads",
                "web_video_starts",
                "web_video_completes",
                "web_total_session_duration",
                "web_avg_session_duration",
                "web_max_session_duration",
                "web_active_days",
                "web_content_type_diversity",
                "web_device_diversity",
                "last_web_ts",
                "last_web_eng_ts",
            ]
        )

    df = df.merge(w_agg, on="hcp_id", how="left")
    df["web_recency"] = (
        (T - df["last_web_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df["web_eng_recency"] = (
        (T - df["last_web_eng_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df.drop(columns=["last_web_ts", "last_web_eng_ts"], inplace=True)

    # Event / Webinar features
    ev = evt[(evt["ts"] >= hist_start) & (evt["ts"] < T)]
    if not ev.empty:
        ev_agg = (
            ev.groupby("hcp_id")
            .agg(
                event_registrations=(
                    "event_activity_type",
                    lambda x: (x == "registration").sum(),
                ),
                event_attendances=(
                    "attendance_status",
                    lambda x: (x == "Attended").sum(),
                ),
                event_total_duration=("attendance_duration_minutes", "sum"),
                event_avg_duration=("attendance_duration_minutes", "mean"),
                event_max_duration=("attendance_duration_minutes", "max"),
                event_questions=("questions_asked", "sum"),
                event_polls=("poll_responses", "sum"),
                event_active_days=("date", "nunique"),
                event_unique_events=("event_id", "nunique"),
                last_event_ts=("ts", "max"),
            )
            .reset_index()
        )
        ev_eng = (
            ev[ev["attendance_status"] == "Attended"]
            .groupby("hcp_id")["ts"]
            .max()
            .reset_index()
            .rename(columns={"ts": "last_event_eng_ts"})
        )
        ev_agg = ev_agg.merge(ev_eng, on="hcp_id", how="left")
    else:
        ev_agg = pd.DataFrame(
            columns=[
                "hcp_id",
                "event_registrations",
                "event_attendances",
                "event_total_duration",
                "event_avg_duration",
                "event_max_duration",
                "event_questions",
                "event_polls",
                "event_active_days",
                "event_unique_events",
                "last_event_ts",
                "last_event_eng_ts",
            ]
        )

    df = df.merge(ev_agg, on="hcp_id", how="left")
    df["event_recency"] = (
        (T - df["last_event_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df["event_eng_recency"] = (
        (T - df["last_event_eng_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df.drop(columns=["last_event_ts", "last_event_eng_ts"], inplace=True)

    # Veeva features
    vv = veeva[(veeva["ts"] >= hist_start) & (veeva["ts"] < T)]
    if not vv.empty:
        vv_agg = (
            vv.groupby("hcp_id")
            .agg(
                veeva_total_interactions=("veeva_event_id", "count"),
                veeva_completed=(
                    "interaction_status",
                    lambda x: (x == "Completed").sum(),
                ),
                veeva_cancelled=(
                    "interaction_status",
                    lambda x: (x == "Cancelled").sum(),
                ),
                veeva_no_show=(
                    "interaction_status",
                    lambda x: (x == "No Show").sum(),
                ),
                veeva_in_person=(
                    "interaction_type",
                    lambda x: (x == "In-Person Visit").sum(),
                ),
                veeva_phone=(
                    "interaction_type",
                    lambda x: (x == "Phone Call").sum(),
                ),
                veeva_virtual=(
                    "interaction_type",
                    lambda x: (x == "Virtual Meeting").sum(),
                ),
                veeva_total_duration=("interaction_duration_minutes", "sum"),
                veeva_avg_duration=("interaction_duration_minutes", "mean"),
                veeva_max_duration=("interaction_duration_minutes", "max"),
                veeva_followups=(
                    "follow_up_required",
                    lambda x: (
                        (x == True).sum()
                        if x.dtype == bool
                        else (x == "Yes").sum()
                    ),
                ),
                veeva_active_days=("date", "nunique"),
                last_veeva_ts=("ts", "max"),
            )
            .reset_index()
        )
        vv_eng = (
            vv[vv["interaction_status"] == "Completed"]
            .groupby("hcp_id")["ts"]
            .max()
            .reset_index()
            .rename(columns={"ts": "last_veeva_eng_ts"})
        )
        vv_agg = vv_agg.merge(vv_eng, on="hcp_id", how="left")
    else:
        vv_agg = pd.DataFrame(
            columns=[
                "hcp_id",
                "veeva_total_interactions",
                "veeva_completed",
                "veeva_cancelled",
                "veeva_no_show",
                "veeva_in_person",
                "veeva_phone",
                "veeva_virtual",
                "veeva_total_duration",
                "veeva_avg_duration",
                "veeva_max_duration",
                "veeva_followups",
                "veeva_active_days",
                "last_veeva_ts",
                "last_veeva_eng_ts",
            ]
        )

    df = df.merge(vv_agg, on="hcp_id", how="left")
    df["veeva_recency"] = (
        (T - df["last_veeva_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df["veeva_eng_recency"] = (
        (T - df["last_veeva_eng_ts"]).dt.total_seconds() / 86400.0
    ).fillna(lookback_days).clip(upper=lookback_days)
    df.drop(columns=["last_veeva_ts", "last_veeva_eng_ts"], inplace=True)

    # Fill count and duration NaNs with 0
    num_cols = [
        c
        for c in df.columns
        if c
        not in [
            "hcp_id",
            "email_recency",
            "email_eng_recency",
            "web_recency",
            "web_eng_recency",
            "event_recency",
            "event_eng_recency",
            "veeva_recency",
            "veeva_eng_recency",
        ]
    ]
    df[num_cols] = df[num_cols].fillna(0)

    # Ratios
    df["email_open_rate"] = df["email_open"] / (df["email_delivered"] + 1e-5)
    df["email_click_rate"] = df["email_click"] / (df["email_delivered"] + 1e-5)
    df["email_ctor"] = df["email_click"] / (df["email_open"] + 1e-5)
    df["web_download_rate"] = df["web_downloads"] / (
        df["web_content_views"] + 1e-5
    )
    df["web_video_completion_rate"] = df["web_video_completes"] / (
        df["web_video_starts"] + 1e-5
    )
    df["event_attendance_rate"] = df["event_attendances"] / (
        df["event_registrations"] + 1e-5
    )
    df["veeva_completion_rate"] = df["veeva_completed"] / (
        df["veeva_total_interactions"] + 1e-5
    )
    df["veeva_followup_rate"] = df["veeva_followups"] / (
        df["veeva_total_interactions"] + 1e-5
    )

    # Cross Channel
    df["total_touchpoints"] = (
        df["email_delivered"]
        + df["web_total_events"]
        + df["event_registrations"]
        + df["veeva_total_interactions"]
    )
    df["active_channels_count"] = (
        (df["email_delivered"] > 0).astype(int)
        + (df["web_total_events"] > 0).astype(int)
        + (df["event_registrations"] > 0).astype(int)
        + (df["veeva_total_interactions"] > 0).astype(int)
    )
    df["email_prop"] = df["email_delivered"] / (df["total_touchpoints"] + 1e-5)
    df["web_prop"] = df["web_total_events"] / (df["total_touchpoints"] + 1e-5)
    df["event_prop"] = df["event_registrations"] / (
        df["total_touchpoints"] + 1e-5
    )
    df["veeva_prop"] = df["veeva_total_interactions"] / (
        df["total_touchpoints"] + 1e-5
    )
    df["digital_touchpoints"] = df["email_delivered"] + df["web_total_events"]
    df["field_touchpoints"] = (
        df["event_registrations"] + df["veeva_total_interactions"]
    )
    df["digital_to_field_ratio"] = df["digital_touchpoints"] / (
        df["field_touchpoints"] + 1.0
    )
    df["min_recency_days"] = df[
        ["email_recency", "web_recency", "event_recency", "veeva_recency"]
    ].min(axis=1)

    # Static normalized features
    df = df.merge(norm, on="hcp_id", how="left")

    # High-intent future targets for balanced 75% performance target
    fut_end = T + pd.Timedelta(days=30)
    e_fut = set(
        email[
            (email["ts"] >= T)
            & (email["ts"] < fut_end)
            & (email["event_type"] == "click")
        ]["hcp_id"]
    )
    w_fut = set(
        web[
            (web["ts"] >= T)
            & (web["ts"] < fut_end)
            & (web["event_type"].isin(["download", "video_complete"]))
        ]["hcp_id"]
    )
    ev_fut = set(
        evt[
            (evt["ts"] >= T)
            & (evt["ts"] < fut_end)
            & (evt["attendance_status"] == "Attended")
        ]["hcp_id"]
    )
    v_fut = set(
        veeva[
            (veeva["ts"] >= T)
            & (veeva["ts"] < fut_end)
            & (veeva["interaction_status"] == "Completed")
        ]["hcp_id"]
    )

    df["email_target"] = df["hcp_id"].isin(e_fut).astype(int)
    df["web_target"] = df["hcp_id"].isin(w_fut).astype(int)
    df["webinar_target"] = df["hcp_id"].isin(ev_fut).astype(int)
    df["veeva_target"] = df["hcp_id"].isin(v_fut).astype(int)

    return df


# 3. Create Snapshots
df_t1 = build_snapshot_dataset(pd.Timestamp("2026-03-01"))
df_t2 = build_snapshot_dataset(pd.Timestamp("2026-04-01"))
df_t3 = build_snapshot_dataset(pd.Timestamp("2026-05-01"))
df_val = build_snapshot_dataset(pd.Timestamp("2026-06-01"))
df_test = build_snapshot_dataset(pd.Timestamp("2026-07-01"))
df_curr = build_snapshot_dataset(pd.Timestamp("2026-08-15"))

df_train = pd.concat([df_t1, df_t2, df_t3], ignore_index=True)

feature_cols = [
    c
    for c in df_train.columns
    if c
    not in ["hcp_id", "email_target", "web_target", "webinar_target", "veeva_target"]
]

# 4. Fit Train PCA for Historical Engagement Score
scaler_pca = StandardScaler()
X_tr_scaled = scaler_pca.fit_transform(df_train[feature_cols])

pca = PCA(n_components=1, random_state=42)
pc1_tr = pca.fit_transform(X_tr_scaled).ravel()

corr = np.corrcoef(pc1_tr, df_train["total_touchpoints"])[0, 1]
pca_sign = 1.0 if corr >= 0 else -1.0
pc1_oriented_tr = pc1_tr * pca_sign

min_pc1 = pc1_oriented_tr.min()
max_pc1 = pc1_oriented_tr.max()


def compute_hist_score(df_in):
    X_scaled = scaler_pca.transform(df_in[feature_cols])
    pc1 = pca.transform(X_scaled).ravel() * pca_sign
    score = (pc1 - min_pc1) / (max_pc1 - min_pc1) * 100.0
    return np.clip(score, 0.0, 100.0)


df_train["Historical_Engagement_Score"] = compute_hist_score(df_train)
df_val["Historical_Engagement_Score"] = compute_hist_score(df_val)
df_test["Historical_Engagement_Score"] = compute_hist_score(df_test)
df_curr["Historical_Engagement_Score"] = compute_hist_score(df_curr)


# 5. Train LightGBM Models & Tune Thresholds for ~75% Target Accuracy
target_map = {
    "Email": "email_target",
    "Website": "web_target",
    "Webinar": "webinar_target",
    "Veeva": "veeva_target",
}

models = {}
calibrated_models = {}
best_thresholds = {}
metrics_records = []

for model_name, target_col in target_map.items():
    clf = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=4,
        num_leaves=15,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )
    clf.fit(df_train[feature_cols], df_train[target_col])
    models[model_name] = clf

    calibrator = CalibratedClassifierCV(
        estimator=FrozenEstimator(clf), method="sigmoid"
    )
    calibrator.fit(df_val[feature_cols], df_val[target_col])
    calibrated_models[model_name] = calibrator

    # Tune classification threshold on Validation set to target ~75% Accuracy
    val_probs = calibrator.predict_proba(df_val[feature_cols])[:, 1]
    best_th = 0.5
    best_diff = 1.0
    for th in np.linspace(0.1, 0.9, 81):
        acc = accuracy_score(df_val[target_col], (val_probs >= th).astype(int))
        if abs(acc - 0.75) < best_diff:
            best_diff = abs(acc - 0.75)
            best_th = th
    best_thresholds[model_name] = best_th

    for split_name, df_split in [("Validation", df_val), ("Final Test", df_test)]:
        probs = calibrator.predict_proba(df_split[feature_cols])[:, 1]
        preds = (probs >= best_th).astype(int)

        auc = roc_auc_score(df_split[target_col], probs)
        pr = average_precision_score(df_split[target_col], probs)
        acc = accuracy_score(df_split[target_col], preds)
        prec = precision_score(df_split[target_col], preds, zero_division=0)
        rec = recall_score(df_split[target_col], preds, zero_division=0)
        f1 = f1_score(df_split[target_col], preds, zero_division=0)

        metrics_records.append(
            {
                "Model": model_name,
                "Dataset_Split": split_name,
                "ROC_AUC": round(float(auc), 4),
                "PR_AUC": round(float(pr), 4),
                "Accuracy": round(float(acc), 4),
                "Precision": round(float(prec), 4),
                "Recall": round(float(rec), 4),
                "F1": round(float(f1), 4),
            }
        )

df_metrics = pd.DataFrame(metrics_records)
df_metrics.to_csv(os.path.join(OUTPUT_DIR, "model_metrics.csv"), index=False)

# Calibrated probabilities
prob_cols = {
    "Email": "Email_Probability",
    "Website": "Website_Probability",
    "Webinar": "Webinar_Probability",
    "Veeva": "Veeva_Probability",
}

for m_name, p_col in prob_cols.items():
    df_val[p_col] = calibrated_models[m_name].predict_proba(
        df_val[feature_cols]
    )[:, 1]
    df_test[p_col] = calibrated_models[m_name].predict_proba(
        df_test[feature_cols]
    )[:, 1]
    df_curr[p_col] = calibrated_models[m_name].predict_proba(
        df_curr[feature_cols]
    )[:, 1]

# 6. Validation Future Reference & Channel Weight Selection
val_future_intensity = (
    df_val["email_target"]
    + df_val["web_target"]
    + df_val["webinar_target"]
    + df_val["veeva_target"]
)

candidate_channel_weights = [
    (0.25, 0.25, 0.25, 0.25),
    (0.30, 0.30, 0.20, 0.20),
    (0.35, 0.25, 0.20, 0.20),
    (0.20, 0.35, 0.25, 0.20),
    (0.25, 0.35, 0.20, 0.20),
]

best_channel_corr = -1.0
best_channel_weights = candidate_channel_weights[0]

for w_e, w_w, w_eb, w_v in candidate_channel_weights:
    val_pred_score = 100.0 * (
        df_val["Email_Probability"] * w_e
        + df_val["Website_Probability"] * w_w
        + df_val["Webinar_Probability"] * w_eb
        + df_val["Veeva_Probability"] * w_v
    )
    corr, _ = spearmanr(val_pred_score, val_future_intensity)
    if corr > best_channel_corr:
        best_channel_corr = corr
        best_channel_weights = (w_e, w_w, w_eb, w_v)

w_e, w_w, w_eb, w_v = best_channel_weights


def compute_pred_score(df_in):
    score = 100.0 * (
        df_in["Email_Probability"] * w_e
        + df_in["Website_Probability"] * w_w
        + df_in["Webinar_Probability"] * w_eb
        + df_in["Veeva_Probability"] * w_v
    )
    return np.clip(score, 0.0, 100.0)


df_val["Predicted_Engagement_Score"] = compute_pred_score(df_val)
df_test["Predicted_Engagement_Score"] = compute_pred_score(df_test)
df_curr["Predicted_Engagement_Score"] = compute_pred_score(df_curr)

# 7. Hybrid Score Weight Selection
candidate_hybrid_weights = [
    (0.20, 0.80),
    (0.30, 0.70),
    (0.40, 0.60),
    (0.50, 0.50),
    (0.60, 0.40),
    (0.70, 0.30),
    (0.80, 0.20),
]

best_hybrid_corr = -1.0
best_hybrid_weights = (0.40, 0.60)

for w_hist, w_pred in candidate_hybrid_weights:
    val_hybrid = (
        df_val["Historical_Engagement_Score"] * w_hist
        + df_val["Predicted_Engagement_Score"] * w_pred
    )
    corr, _ = spearmanr(val_hybrid, val_future_intensity)
    if corr > best_hybrid_corr:
        best_hybrid_corr = corr
        best_hybrid_weights = (w_hist, w_pred)

w_hist, w_pred = best_hybrid_weights


def compute_hybrid_score(df_in):
    score = (
        df_in["Historical_Engagement_Score"] * w_hist
        + df_in["Predicted_Engagement_Score"] * w_pred
    )
    return np.clip(score, 0.0, 100.0)


df_val["Hybrid_Engagement_Score"] = compute_hybrid_score(df_val)
df_test["Hybrid_Engagement_Score"] = compute_hybrid_score(df_test)
df_curr["Hybrid_Engagement_Score"] = compute_hybrid_score(df_curr)

# 8. Engagement Level Quantile Thresholds
q33 = df_val["Hybrid_Engagement_Score"].quantile(0.3333)
q66 = df_val["Hybrid_Engagement_Score"].quantile(0.6667)


def assign_engagement_level(score):
    if score < q33:
        return "Low"
    elif score < q66:
        return "Medium"
    else:
        return "High"


df_curr["Engagement_Level"] = df_curr["Hybrid_Engagement_Score"].apply(
    assign_engagement_level
)

# 9. Next Best Channel
channel_names = ["Email", "Website", "Webinar", "Veeva"]
prob_matrix = df_curr[
    [
        "Email_Probability",
        "Website_Probability",
        "Webinar_Probability",
        "Veeva_Probability",
    ]
].values
best_channel_idx = np.argmax(prob_matrix, axis=1)
df_curr["Next_Best_Channel"] = [channel_names[i] for i in best_channel_idx]

# 10. SHAP Explanations & Recommended Reason
explainers = {m_name: shap.TreeExplainer(clf) for m_name, clf in models.items()}
shap_values_dict = {
    m_name: explainers[m_name].shap_values(df_curr[feature_cols])
    for m_name in models
}

feature_desc_map = {
    "event_attendances": "recent event attendance",
    "event_attendance_rate": "high webinar participation consistency",
    "event_total_duration": "sustained webinar watch duration",
    "event_questions": "active Q&A engagement during medical events",
    "event_recency": "recent medical conference attendance",
    "norm_event_attendance": "strong historical webinar presence",
    "veeva_completed": "completed field representative visits",
    "veeva_completion_rate": "high visit completion rate",
    "veeva_in_person": "face-to-face interaction history",
    "veeva_recency": "recent representative interaction",
    "norm_completed_interactions": "frequent representative touchpoints",
    "web_content_views": "frequent clinical article views",
    "web_downloads": "active downloading of clinical PDF resources",
    "web_video_completes": "full views of educational video content",
    "web_recency": "recent portal navigation",
    "norm_web_content_views": "consistent website content browsing",
    "email_open": "consistent email open activity",
    "email_click": "active engagement with email links",
    "email_open_rate": "high email open responsiveness",
    "email_recency": "recent email engagement",
    "norm_email_open_rate": "strong historical email responsiveness",
    "total_touchpoints": "high overall cross-channel activity",
    "active_channels_count": "multi-channel responsiveness",
}

reasons = []
for idx in range(len(df_curr)):
    nbc = df_curr.loc[idx, "Next_Best_Channel"]
    prob = df_curr.loc[idx, f"{nbc}_Probability"]

    s_vals = shap_values_dict[nbc]
    hcp_shap = s_vals[1][idx] if isinstance(s_vals, list) else s_vals[idx]
    top_feat_indices = np.argsort(hcp_shap)[::-1]
    pos_feats = [feature_cols[i] for i in top_feat_indices if hcp_shap[i] > 0]

    top_reasons = []
    for f in pos_feats:
        if f in feature_desc_map and feature_desc_map[f] not in top_reasons:
            top_reasons.append(feature_desc_map[f])
        if len(top_reasons) >= 2:
            break

    if len(top_reasons) == 0:
        reason = f"{nbc} is recommended with {prob:.1%} predicted likelihood based on positive overall behavioral affinity across channels."
    elif len(top_reasons) == 1:
        reason = f"{nbc} is recommended with {prob:.1%} predicted likelihood because the HCP has shown {top_reasons[0]}, which positively influences predicted {nbc.lower()} engagement."
    else:
        reason = f"{nbc} is recommended with {prob:.1%} predicted likelihood because the HCP has shown {top_reasons[0]} and {top_reasons[1]}, which positively influence predicted {nbc.lower()} engagement."

    reasons.append(reason)

df_curr["Recommended_Reason"] = reasons

# 11. Final Output CSV
final_cols = [
    "HCP_ID",
    "Historical_Engagement_Score",
    "Predicted_Engagement_Score",
    "Hybrid_Engagement_Score",
    "Engagement_Level",
    "Email_Probability",
    "Website_Probability",
    "Webinar_Probability",
    "Veeva_Probability",
    "Next_Best_Channel",
    "Recommended_Reason",
]

df_curr["HCP_ID"] = df_curr["hcp_id"]
df_out = df_curr[final_cols].copy()

df_out["Historical_Engagement_Score"] = df_out[
    "Historical_Engagement_Score"
].round(2)
df_out["Predicted_Engagement_Score"] = df_out["Predicted_Engagement_Score"].round(
    2
)
df_out["Hybrid_Engagement_Score"] = df_out["Hybrid_Engagement_Score"].round(2)

df_out["Email_Probability"] = df_out["Email_Probability"].round(4)
df_out["Website_Probability"] = df_out["Website_Probability"].round(4)
df_out["Webinar_Probability"] = df_out["Webinar_Probability"].round(4)
df_out["Veeva_Probability"] = df_out["Veeva_Probability"].round(4)

df_out.to_csv(
    os.path.join(OUTPUT_DIR, "hcp_engagement_predictions.csv"), index=False
)

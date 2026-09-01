# Spec 02: Model Training & Evaluation

**Version**: 1.1 (Simplified - XGBoost only, single notebook)
**Date**: 31 Agustus 2026
**Related PRD**: FR-2, Section 9

---

## Tujuan

Melatih model klasifikasi XGBoost untuk membedakan traffic HTTP `normal` vs `anomalous` menggunakan dataset CSIC 2010 dari folder `./sample/training`. Seluruh pipeline (EDA hingga evaluasi) dijalankan dalam satu notebook Jupyter.

---

## Struktur Folder

```
notebooks/
└── 01-xgboost-training.ipynb      # Semua langkah dalam 1 notebook

models/
├── xgboost_model.pkl              # Model trained XGBoost (best hyperparameters)
└── xgboost_metadata.json          # Metadata model
```

> **Catatan**: Tidak ada folder `scripts/` atau model eksperimental lain. Semua berjalan via notebook.

---

## Dataset

### Sumber Data

Dataset dibaca langsung dari folder `./sample/training`:

| File | Label | Deskripsi |
|------|-------|-----------|
| `normal.txt` | `normal` (label: 0) | Traffic HTTP normal (CSIC 2010) |
| `anomalous.txt` | `anomalous` (label: 1) | Traffic HTTP anomalous (gabungan semua kelas serangan) |

### Format Input

Kedua file menggunakan format **raw HTTP request log text** (format CSIC 2010 asli), dipisah oleh double newline (`\n\n`). Setiap block berisi:

```
METHOD http://host/path?key=val HTTP/1.1
Header-Key: Header-Value
...

[potential body untuk POST request]
```

Parser otomatis mengubah menjadi dict terstruktur sesuai **Spec 01 (Feature Extraction)**:

```python
{
    'method': 'GET',
    'full_url': 'http://localhost:8080/tienda1/index.jsp',
    'path': '/tienda1/index.jsp',
    'query_string': '',
    'query_params': {},
    'headers': {'user-agent': '...', 'host': 'localhost:8080', ...},
    'body': '',
    'content_length': 0
}
```

---

## Struktur Notebook

Notebook `01-xgboost-training.ipynb` dibagi menjadi section-section berikut (menggunakan heading markdown `#`):

### Section 1: Imports dan Konfigurasi

```python
# Import libraries utama
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Feature extraction
from src.feature_extraction.parser import HTTPRequestParser
from src.feature_extraction.dataset_loader import CSICDatasetLoader
from src.feature_extraction.extractor import FeatureExtractor

# ML Libraries
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, 
    precision_recall_curve, roc_curve
)
import xgboost as xgb
import optuna
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

# Konfigurasi
DATA_DIR = Path('./sample/training')
OUTPUT_DIR = Path('./models')
RANDOM_STATE = 42
TEST_SIZE = 0.2
```

### Section 2: Load Data

```python
# Inisialisasi loader
loader = CSICDatasetLoader(data_dir=str(DATA_DIR))

# Load dataset
df = loader.load()
# Output: Loaded N total requests ({'anomalous': X, 'normal': Y})

# Tampilkan info dasar
print(f"Total samples: {len(df)}")
print(f"\nClass distribution:\n{df['label'].value_counts()}")
print(f"\nSample parsed request:")
print(json.dumps(df['parsed_json'].iloc[0], indent=2))
```

### Section 3: Exploratory Data Analysis (EDA)

#### 3.1 Distribution of Request Methods

```python
df['parsed_json'].apply(lambda x: x['method']).value_counts().plot(kind='bar')
plt.title('Distribution of Request Methods')
plt.xlabel('Method')
plt.ylabel('Count')
plt.show()
```

#### 3.2 URL Length Analysis by Class

```python
df['url_len'] = df['parsed_json'].apply(lambda x: len(x['full_url']))
df.groupby('label')['url_len'].describe()

sns.boxplot(data=df, x='label', y='url_len')
plt.title('URL Length Distribution by Class')
plt.show()
```

#### 3.3 Payload Body Analysis

```python
df['payload_len'] = df['parsed_json'].apply(lambda x: len(x['body']))

# Bandingkan payload length antara normal dan anomalous
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

for label, ax in zip(['normal', 'anomalous'], axes):
    subset = df[df['label'] == label]['payload_len']
    ax.hist(subset, bins=30, edgecolor='black')
    ax.set_title(f'{label.capitalize()} - Payload Length')
    ax.set_xlabel('Payload Length')
    ax.set_ylabel('Frequency')

plt.tight_layout()
plt.show()
```

#### 3.4 Query Parameter Count Analysis

```python
df['param_count'] = df['parsed_json'].apply(lambda x: len(x.get('query_params', {})))

sns.violinplot(data=df, x='label', y='param_count')
plt.title('Query Parameter Count by Class')
plt.show()
```

#### 3.5 Header Presence Analysis

```python
# Check common headers presence
common_headers = ['user-agent', 'host', 'cookie', 'content-type', 'accept']

header_presence = {}
for header in common_headers:
    header_presence[f'has_{header}'] = df['parsed_json'].apply(
        lambda x: 1 if header in x.get('headers', {}) else 0
    )

header_df = pd.DataFrame(header_presence)
header_df = pd.concat([header_df, df['label']], axis=1)

# Cross-tabulation
for header in common_headers:
    ct = pd.crosstab(df['label'], header_df[f'has_{header}'])
    print(f"\n{'='*40}")
    print(f"Header: {header}")
    print(ct)
```

#### 3.6 SQL Keyword Detection in Raw Text

```python
import re

SQL_KEYWORDS_PATTERN = re.compile(
    r"(SELECT|UNION|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|"
    r"EXEC|EXECUTE|xp_|sp_|DECLARE|CURSOR|CAST|CONVERT|"
    r"OR\s+1\s*=\s*1|AND\s+1\s*=\s*1)",
    re.IGNORECASE
)

df['raw_sql_match'] = df['parsed_json'].apply(
    lambda x: 1 if SQL_KEYWORDS_PATTERN.search(x['full_url'] + x['body']) else 0
)

print(f"Raw SQL keyword matches in normal: {(df[df['label']=='normal']['raw_sql_match'] == 1).sum()}")
print(f"Raw SQL keyword matches in anomalous: {(df[df['label']=='anomalous']['raw_sql_match'] == 1).sum()}")
```

#### 3.7 Summary Statistics

```python
summary_stats = df.groupby('label').agg(
    count=('label', 'count'),
    avg_url_len=('url_len', 'mean'),
    max_url_len=('url_len', 'max'),
    avg_payload_len=('payload_len', 'mean'),
    max_payload_len=('payload_len', 'max'),
    avg_param_count=('param_count', 'mean')
).round(2)

print(summary_stats)
```

### Section 4: Feature Extraction

```python
# Initialize extractor
extractor = FeatureExtractor()

# Extract features from all samples
print("Extracting features...")
X, y, feature_names = loader.extract_features(df, extractor)
# Output: Extracted N features successfully
#         Shape: X=(N, 32), y=(N,)
#         Class distribution: {0: Y, 1: Z}

# Convert to DataFrame for inspection
feature_df = pd.DataFrame(X, columns=feature_names)
feature_df['label'] = y
print(f"\nFeature matrix shape: {feature_df.shape}")
print(f"\nFirst 5 rows:")
print(feature_df.head())
```

### Section 5: Train/Test Split

```python
# Stratified split
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    stratify=y,
    random_state=RANDOM_STATE
)

print(f"Training set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")
print(f"\nTrain label distribution: {dict(zip(*np.unique(y_train, return_counts=True)))}")
print(f"Test label distribution: {dict(zip(*np.unique(y_test, return_counts=True)))}")
```

### Section 6: Baseline Model (Default Hyperparameters)

```python
# Default baseline parameters
baseline_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 200,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'gamma': 0,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'random_state': RANDOM_STATE
}

# Train baseline model
baseline_model = xgb.XGBClassifier(**baseline_params)
baseline_model.fit(X_train, y_train)

# Evaluate on test set
y_pred_baseline = baseline_model.predict(X_test)
y_proba_baseline = baseline_model.predict_proba(X_test)[:, 1]

accuracy_baseline = baseline_model.score(X_test, y_test)
auc_baseline = roc_auc_score(y_test, y_proba_baseline)

print(f"Baseline Model Performance:")
print(f"  Accuracy: {accuracy_baseline:.4f}")
print(f"  ROC-AUC:  {auc_baseline:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred_baseline, target_names=['normal', 'anomalous']))
```

### Section 7: Cross-Validation

```python
# 5-fold stratified CV
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

cv_scores_f1 = cross_val_score(baseline_model, X_train, y_train, cv=skf, scoring='f1_weighted')
cv_scores_auc = cross_val_score(baseline_model, X_train, y_train, cv=skf, scoring='roc_auc')

print(f"Cross-Validation Results (Baseline):")
print(f"  F1 Weighted:   {cv_scores_f1.mean():.4f} (+/- {cv_scores_f1.std():.4f})")
print(f"  ROC AUC:       {cv_scores_auc.mean():.4f} (+/- {cv_scores_auc.std():.4f})")
```

### Section 8: Hyperparameter Tuning dengan Optuna

```python
def xgb_objective(trial):
    """Objective function untuk Optuna hyperparameter tuning."""
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'logloss',
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 1),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 1),
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 0.5, 2.0),
        'random_state': RANDOM_STATE
    }
    
    model = xgb.XGBClassifier(**params)
    scores = cross_val_score(model, X_train, y_train, cv=skf, scoring='f1_weighted')
    return scores.mean()

# Run Optuna study
study = optuna.create_study(direction='maximize')
study.optimize(xgb_objective, n_trials=50)

print(f"Best Trial:")
print(f"  Value: {study.best_value:.4f}")
print(f"  Params: {study.best_params}")

# Best parameters
best_params = study.best_params
best_params.update({
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'random_state': RANDOM_STATE
})
```

### Section 9: Final Model Training

```python
# Train final model with best hyperparameters
final_model = xgb.XGBClassifier(**best_params)
final_model.fit(X_train, y_train)

# Full evaluation
y_pred_final = final_model.predict(X_test)
y_proba_final = final_model.predict_proba(X_test)[:, 1]

print("=" * 50)
print("FINAL MODEL PERFORMANCE (Best Hyperparameters)")
print("=" * 50)
print(f"Accuracy:  {final_model.score(X_test, y_test):.4f}")
print(f"ROC-AUC:   {roc_auc_score(y_test, y_proba_final):.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred_final, target_names=['normal', 'anomalous']))

# Compare with baseline
print("\nCOMPARISON: Baseline vs Final Model")
comparison = pd.DataFrame({
    'Metric': ['Accuracy', 'ROC-AUC'],
    'Baseline': [accuracy_baseline, auc_baseline],
    'Final': [final_model.score(X_test, y_test), roc_auc_score(y_test, y_proba_final)]
})
print(comparison)
```

### Section 10: Evaluation Metrics & Visualizations

#### 10.1 Confusion Matrix

```python
cm = confusion_matrix(y_test, y_pred_final)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['normal', 'anomalous'],
            yticklabels=['normal', 'anomalous'])
plt.title('Confusion Matrix - Final Model')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'confusion_matrix.png', dpi=150)
plt.show()
```

#### 10.2 ROC Curve

```python
fpr, tpr, _ = roc_curve(y_test, y_proba_final)
auc_value = roc_auc_score(y_test, y_proba_final)

plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='blue', lw=2, label=f'XGBoost (AUC = {auc_value:.4f})')
plt.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--')
plt.fill_between(fpr, tpr, alpha=0.2, color='blue')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc='lower right')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'roc_curve.png', dpi=150)
plt.show()
```

#### 10.3 Precision-Recall Curve

```python
precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_proba_final)

plt.figure(figsize=(8, 6))
plt.plot(recall_vals, precision_vals, color='blue', lw=2)
plt.fill_between(recall_vals, precision_vals, alpha=0.2, color='blue')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'precision_recall_curve.png', dpi=150)
plt.show()
```

#### 10.4 Feature Importance

```python
# Get feature importances
importances = final_model.feature_importances_
feat_imp = pd.DataFrame({
    'feature': feature_names,
    'importance': importances
}).sort_values('importance', ascending=False)

# Top 15 features
top_n = 15
top_features = feat_imp.head(top_n)

plt.figure(figsize=(10, 8))
plt.barh(range(top_n), top_features['importance'].values[::-1], color='steelblue')
plt.yticks(range(top_n), top_features['feature'].values[::-1])
plt.xlabel('Importance (Gain)')
plt.title(f'Top {top_n} Feature Importances')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'feature_importance.png', dpi=150)
plt.show()

print("\nTop 10 Most Important Features:")
print(feat_imp.head(10).to_string(index=False))
```

### Section 11: Threshold Tuning (Optional)

```python
# Find optimal threshold for minimal FPR
thresholds = np.arange(0.1, 0.9, 0.01)
results = []

for threshold in thresholds:
    preds_tuned = (y_proba_final >= threshold).astype(int)
    
    tn, fp, fn, tp = confusion_matrix(y_test, preds_tuned).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    
    results.append({
        'threshold': threshold,
        'fpr': fpr,
        'fnr': fnr,
        'precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
        'recall': tp / (tp + fn) if (tp + fn) > 0 else 0
    })

threshold_df = pd.DataFrame(results)

# Plot FPR and FNR vs threshold
plt.figure(figsize=(10, 6))
plt.plot(threshold_df['threshold'], threshold_df['fpr'], label='FPR', color='red')
plt.plot(threshold_df['threshold'], threshold_df['fnr'], label='FNR', color='orange')
plt.xlabel('Threshold')
plt.ylabel('Rate')
plt.title('FPR and FNR vs Classification Threshold')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# Suggest optimal threshold (balance FPR and FNR)
threshold_df['balance_score'] = abs(threshold_df['fpr'] - threshold_df['fnr'])
optimal_row = threshold_df.loc[threshold_df['balance_score'].idxmin()]
print(f"Suggested Threshold: {optimal_row['threshold']:.2f}")
print(f"  FPR: {optimal_row['fpr']:.4f}")
print(f"  FNR: {optimal_row['fnr']:.4f}")
```

### Section 12: Save Model & Metadata

```python
# Create output directory if not exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Save model
joblib.dump(final_model, OUTPUT_DIR / 'xgboost_model.pkl')
print(f"Model saved to {OUTPUT_DIR / 'xgboost_model.pkl'}")

# Calculate final metrics
final_accuracy = final_model.score(X_test, y_test)
final_auc = roc_auc_score(y_test, y_proba_final)
final_report = classification_report(y_test, y_pred_final, output_dict=True, target_names=['normal', 'anomalous'])

# Save metadata
metadata = {
    'model_type': 'XGBoost',
    'version': '1.0.0',
    'training_date': pd.Timestamp.now().strftime('%Y-%m-%d'),
    'feature_names': feature_names,
    'num_features': len(feature_names),
    'hyperparameters': best_params,
    'dataset_info': {
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'source_files': ['normal.txt', 'anomalous.txt'],
        'data_directory': str(DATA_DIR)
    },
    'metrics': {
        'accuracy': float(final_accuracy),
        'roc_auc': float(final_auc),
        'precision_normal': float(final_report['normal']['precision']),
        'recall_normal': float(final_report['normal']['recall']),
        'f1_normal': float(final_report['normal']['f1-score']),
        'precision_anomalous': float(final_report['anomalous']['precision']),
        'recall_anomalous': float(final_report['anomalous']['recall']),
        'f1_anomalous': float(final_report['anomalous']['f1-score'])
    },
    'feature_importance_top15': feat_imp.head(15).to_dict(orient='records')
}

with open(OUTPUT_DIR / 'xgboost_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"Metadata saved to {OUTPUT_DIR / 'xgboost_metadata.json'}")
print("\n" + "=" * 50)
print("TRAINING COMPLETE!")
print("=" * 50)
```

---

## Evaluasi

### Metrics Target

| Metric | Target | Catatan |
|--------|--------|---------|
| Overall Accuracy | >= 95% | Berbasis benchmark literatur CSIC 2010 |
| Precision (anomalous) | >= 94% | Minim false positive |
| Recall (anomalous) | >= 93% | Deteksi sebagian besar serangan |
| F1-Score (anomalous) | >= 93% | Balanced metric |
| ROC-AUC | >= 0.98 | Area under ROC curve |
| False Positive Rate | <= 2% | Critical untuk UX |

### Confusion Matrix Layout

```
                 Predicted
                 Normal  Anomalous
Actual Normal     TN       FP
       Anomalous  FN       TP
```

Target: FP dan FN seminimal mungkin.

---

## Acceptance Criteria

- [ ] Notebook `notebooks/01-xgboost-training.ipynb` berhasil menjalankan seluruh pipeline tanpa error
- [ ] Dataset dari `./sample/training` berhasil dibaca (normal.txt + anomalous.txt)
- [ ] Feature extraction menghasilkan 32 fitur sesuai Spec 01
- [ ] Model XGBoost terlatih dengan akurasi >= 95% pada test set
- [ ] Precision >= 94%, Recall >= 93%, F1 >= 93% untuk kelas `anomalous`
- [ ] False positive rate <= 2% pada traffic normal
- [ ] Feature importance diextract dan divisualisasikan (top 15)
- [ ] Model disimpan di `models/xgboost_model.pkl`
- [ ] Metadata disimpan di `models/xgboost_metadata.json` (termasuk hyperparameters, metrics, feature names)
- [ ] Visualisasi confusion matrix, ROC curve, PR curve, dan feature importance tersimpan di `models/`
- [ ] Notebook dapat dijalankan ulang (reproducible) dengan fixed random seed

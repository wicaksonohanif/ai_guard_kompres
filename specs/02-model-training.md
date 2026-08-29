# Spec 02: Model Training & Evaluation

**Version**: 1.0
**Date**: 29 Agustus 2026
**Related PRD**: FR-2, Section 9

---

## Tujuan

Melatih model klasifikasi XGBoost untuk membedakan traffic HTTP `normal` vs `anomalous` menggunakan dataset CSIC 2010, dengan evaluasinya, serta menjalankan eksperimen pembanding (LSTM/CNN) untuk laporan kompetisi.

---

## Dataset

### Primary: CSIC 2010 HTTP Dataset

| Kelas | Label | Deskripsi |
|-------|-------|-----------|
| Normal | `normal` | Traffic HTTP normal |
| Attack: attack_generic | `anomalous` | Serangan umum |
| Attack: sql_injection | `anomalous` | SQL Injection |
| Attack: cross_site_scripting | `anomalous` | XSS |
| Attack: remote_file_creation | `anomalous` | Remote file creation |
| Attack: local_file_creation | `anomalous` | Local file creation |
| Attack: iis_path_traversal | `anomalous` | IIS path traversal |
| Attack: linux_path_traversal | `anomalous` | Linux path traversal |
| Attack: index insertion | `anomalous` | Index insertion |
| Attack: directory listing | `anomalous` | Directory listing |
| Attack: login page tampering | `anomalous` | Login tampering |
| Attack: parameter padding | `anomalous` | Parameter padding |
| Attack: parameter manipulation discovery | `anomalous` | Parameter manipulation |
| Attack: header manipulation | `anomalous` | Header manipulation |
| Attack: buffer overflow | `anomalous` | Buffer overflow |
| Attack: CRLF injection | `anomalous` | CRLF injection |
| Attack: SSI injection | `anomalous` | SSI injection |

Mapping ke binary classification:
- `Normal` -> `normal` (label: 0)
- Semua kelas attack -> `anomalous` (label: 1)

Multi-class juga tersedia untuk analisis per-kelas.

### Supplementary: Self-Generated Traffic

Generate traffic tambahan dari prototipe website:
- Traffic normal: browsing halaman website
- Traffic anomalous: kirim payload serangan melalui simulation tool (Spec 08)
- Data ini ditambahkan untuk mengurangi gap antara dataset CSIC 2010 dan traffic nyata

---

## Preprocessing

### 2.1 Handling Missing Values

- Dataset CSIC 2010 seharusnya lengkap (tidak ada missing values)
- Validasi dengan assertion: `assert df.isnull().sum().sum() == 0`

### 2.2 Train/Test Split

```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    features, labels,
    test_size=0.2,
    stratify=labels,       # Preserve class distribution
    random_state=42
)
```

### 2.3 Feature Scaling

- XGBoost tidak memerlukan scaling (tree-based algorithm)
- Namun, untuk eksperimen LSTM/CNN, Normalize/Standardize diperlukan

### 2.4 Encoding

- Label encoding: `normal` -> 0, `anomalous` -> 1
- Multi-class: setiap attack class mendapat integer id unik

---

## Model Utama: XGBoost

### 3.1 Hyperparameters Default (Baseline)

```python
xgb_params = {
    'objective': 'binary:logistic',      # Atau 'multi:softmax' untuk multi-class
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
    'scale_pos_weight': None,             # Tuning needed jika imbalanced
    'random_state': 42
}
```

### 3.2 Training dengan Cross-Validation

```python
from sklearn.model_selection import StratifiedKFold, cross_val_score

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=skf, scoring='f1_weighted')
print(f"F1 Weighted Mean: {scores.mean():.4f} (+/- {scores.std():.4f})")
```

### 3.3 Hyperparameter Tuning

Gunakan **Optuna** untuk hyperparameter optimization:

```python
import optuna

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 1),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 1),
    }
    # Training & evaluation...
    return f1_score  # Maximize F1
```

### 3.4 Saving Model

```python
import joblib
import json

# Save model
joblib.dump(model, 'models/xgboost_model.pkl')

# Save metadata (feature names, version, training date)
metadata = {
    'model_type': 'XGBoost',
    'version': '1.0.0',
    'training_date': '2026-XX-XX',
    'feature_names': feature_names,
    'num_features': len(feature_names),
    'accuracy': accuracy,
    'precision_per_class': precision_dict,
    'recall_per_class': recall_dict
}
with open('models/xgboost_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)
```

---

## Eksperimen Pembanding: LSTM & CNN

*Bukan untuk deployment, hanya untuk laporan kompetisi.*

### 4.1 Character-Level Input

Untuk LSTM/CNN, gunakan raw HTTP request URI/body sebagai karakter-level sequence:

```python
# Tokenisasi karakter
vocab_size = 128  # ASCII range
max_length = 512  # Max length of URL/payload

# Padding
X_padded = pad_sequences(X_tokenized, maxlen=max_length, padding='post')
```

### 4.2 LSTM Architecture

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout

lstm_model = Sequential([
    Embedding(input_dim=vocab_size, output_dim=64, input_length=max_length),
    LSTM(32, return_sequences=False),
    Dropout(0.5),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid')
])
```

### 4.3 CNN Architecture

```python
from tensorflow.keras.layers import Conv1D, GlobalMaxPooling1D

cnn_model = Sequential([
    Embedding(input_dim=vocab_size, output_dim=64, input_length=max_length),
    Conv1D(filters=64, kernel_size=5, activation='relu'),
    GlobalMaxPooling1D(),
    Dropout(0.5),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid')
])
```

### 4.4 Comparison Report

| Model | Accuracy | Precision | Recall | F1-Score | Latency (per prediction) |
|-------|----------|-----------|--------|----------|--------------------------|
| XGBoost | TBD | TBD | TBD | TBD | < 5ms |
| LSTM | TBD | TBD | TBD | TBD | ~20ms |
| CNN | TBD | TBD | TBD | TBD | ~10ms |

---

## Evaluasi

### 5.1 Metrics Per Kelas

```python
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve
)

# Binary classification
print(classification_report(y_test, y_pred, target_names=['normal', 'anomalous']))

# Per anomalous sub-class (multi-class analysis)
# Map predictions back to original CSIC classes
```

### 5.2 Metrics Target

| Metric | Target | Catatan |
|--------|--------|---------|
| Overall Accuracy | >= 95% | Berbasis benchmark literatur CSIC 2010 |
| Precision (anomalous) | >= 94% | Minim false positive |
| Recall (anomalous) | >= 93% | Deteksi sebagian besar serangan |
| F1-Score (anomalous) | >= 93% | Balanced metric |
| ROC-AUC | >= 0.98 | Area under ROC curve |
| False Positive Rate | <= 2% | Critical untuk UX |

### 5.3 Confusion Matrix Analysis

```
                 Predicted
                 Normal  Anomalous
Actual Normal     TN       FP
       Anomalous  FN       TP
```

Target: FP dan FN seminimal mungkin.

### 5.4 Feature Importance

```python
import matplotlib.pyplot as plt

model.feature_importance_  # atau .booster().get_score(importance_type='gain')

# Visualisasi top 15 features
top_features = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)[:15]
plt.barh([f[0] for f in top_features], [f[1] for f in top_features])
plt.title('Top 15 Feature Importances')
plt.tight_layout()
plt.savefig('reports/feature_importance.png')
```

---

## Directory Structure

```
models/
├── xgboost_model.pkl          # Model trained XGBoost
├── xgboost_metadata.json      # Metadata model
├── lstm_model.h5              # Experimental LSTM (opsional)
└── cnn_model.h5               # Experimental CNN (opsional)

notebooks/
├── 01-data-exploration.ipynb
├── 02-preprocessing.ipynb
├── 03-xgboost-baseline.ipynb
├── 04-hyperparameter-tuning.ipynb
├── 05-lstm-cnn-experiment.ipynb
└── 06-evaluation-and-reports.ipynb

scripts/
├── train_xgboost.py           # Training script (reproducible)
├── evaluate_model.py          # Evaluation script
└── generate_reports.py        # Generate reports & charts
```

---

## Acceptance Criteria

- [ ] Model XGBoost terlatih dengan akurasi >= 95% pada test set CSIC 2010
- [ ] Precision >= 94%, Recall >= 93%, F1 >= 93% untuk kelas `anomalous`
- [ ] False positive rate <= 2% pada traffic normal
- [ ] Feature importance diextract dan divisualisasikan
- [ ] Eksperimen LSTM/CNN dijalankan (untuk laporan, bukan deployment)
- [ ] Model disimpan dengan metadata lengkap (version, metrics, feature names)
- [ ] Training dapat di-reproduce (same code -> same results with fixed random seed)

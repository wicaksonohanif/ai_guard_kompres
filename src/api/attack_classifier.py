"""
Heuristic attack class inference berdasarkan signature keyword counts.
Karena model XGBoost hanya binary (normal/anomalous), jenis serangan
ditentukan secara heuristic dari fitur signature yang dihitung oleh FeatureExtractor.
"""

# Mapping dari nama fitur count ke label attack class
SIGNATURE_MAPPING = {
    "sql_keyword_count": "sql_injection",
    "xss_keyword_count": "xss",
    "path_traversal_count": "path_traversal",
    "crlf_injection_count": "crlf_injection",
    "cmd_injection_count": "command_injection",
    "file_inclusion_count": "file_inclusion",
}


def infer_attack_class(features_dict: dict) -> str:
    """
    Tentukan jenis serangan berdasarkan signature keyword count tertinggi.

    Args:
        features_dict: dict dengan key = nama fitur, value = nilai numerik.
                       Diharapkan memiliki key-key dari SIGNATURE_MAPPING.

    Returns:
        str: label jenis serangan ("sql_injection", "xss", "path_traversal",
             "crlf_injection", "command_injection", "file_inclusion")
             atau "unknown_anomaly" jika semua count = 0.
    """
    best_label = "unknown_anomaly"
    best_count = 0

    for feature_key, attack_label in SIGNATURE_MAPPING.items():
        count = features_dict.get(feature_key, 0)
        if count > best_count:
            best_count = count
            best_label = attack_label

    return best_label

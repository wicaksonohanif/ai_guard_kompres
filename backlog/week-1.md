# AI Guard - Sprint Backlog - Week 1

**Version**: 1.2
**Status**: Draft
**Date**: 1 September 2026
**Source**: PRD_AI_Guard.md v1.0

---

| Tahap | Output | Catatan |
|---|---|---|
| Minggu 1 (31/08/26) | *Overview* kendala dari project | **Poin Temuan**: <br> <ul> <li> Kelas yang dapat diprediksi hanya bersifat biner yaitu kelas anomalous dan normal saja, jika kelas anolamous mau dijabarkan lagi jadi serangan apa saja kayaknya cukup sulit karena kelasnya pasti terlalu banyak. </ul> |
| Minggu 1 (01/09/26) | Menjalan *initial check* training notebook 01-xgboost-training.ipynb | **Poin Temuan**: <br> <ul> <li> Notebook [01-xgboost-training.ipynb](kompres\notebooks\01-xgboost-training.ipynb) berhasil dijalankan <li> Model [xgboost (.pkl)](kompres\models\01-xgboost-training\01-xgboost_model.pkl) berhasil dibuat, metrik evaluasi dapat dilihat pada file [metadata](kompres\models\01-xgboost-training\01-xgboost_metadata.json). <li> Secara metrik sudah cukup bagus, namun perlu dibuktikan pada production. <li> Jika ingin lanjut develop aplikasi web, input model harus sesuai format! lihat format pada notebook/metadata dan lakukan preprocessing (feature extraction) data traffic sesuai yang dilakukan di notebook. Ini supaya bisa masuk ke modelnya</ul> |
| Minggu 1 (04/09/26) | Implementasi & verifikasi Spec 03 (Inference API) | **Poin Temuan**: <br> <ul> <li> Endpoint `/predict`, `/predict-batch`, `/health`, `/metrics` berhasil diimplementasi dan diuji end-to-end via curl, seluruhnya lolos dengan latensi rata-rata < 2ms (target < 100ms) <li> Ditemukan bug fatal di contoh kode Spec 03: `query_params` di-hardcode kosong padahal menyumbang >61% feature importance — sudah diperbaiki dengan parsing riil dari query string & body form-urlencoded <li> `attack_class` tidak bisa berbasis ML karena model biner murni; diimplementasi sebagai heuristic signature-count sementara <li> **Ditemukan false positive**: model CSIC 2010 salah mengklasifikasikan request modern sederhana (`GET /home`) sebagai anomalous akibat domain gap (traffic normal training 100% berpola URL Spanyol `tienda1/...`) — ditambal dengan guardrail manual di API, BELUM diperbaiki di level model <li> Perlu keputusan sebelum Step 4: apakah retrain model dengan data traffic modern, apakah attack_class tetap heuristic atau upgrade ke ML multi-class, dan apakah inference API jalan sebagai microservice terpisah atau in-process dengan middleware </ul> |


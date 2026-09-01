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

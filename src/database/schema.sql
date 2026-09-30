CREATE TABLE IF NOT EXISTS traffic_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,source_ip TEXT,source_port INTEGER,method TEXT NOT NULL,url TEXT NOT NULL,full_url TEXT,user_agent TEXT,referer TEXT,content_type TEXT,payload_body TEXT,label TEXT NOT NULL CHECK(label IN ('normal','anomalous')),confidence REAL NOT NULL,attack_class TEXT,action TEXT NOT NULL CHECK(action IN ('allow','flag','block')),inference_latency_ms REAL,feature_count INTEGER,is_blocked INTEGER DEFAULT 0 CHECK(is_blocked IN (0,1)),review_status TEXT DEFAULT 'auto' CHECK(review_status IN ('auto','manual_review','false_positive','confirmed_attack')));
CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON traffic_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_label ON traffic_logs(label);
CREATE INDEX IF NOT EXISTS idx_traffic_attack_class ON traffic_logs(attack_class);
CREATE TABLE IF NOT EXISTS notification_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,traffic_log_id INTEGER REFERENCES traffic_logs(id),sent_at DATETIME,status TEXT NOT NULL CHECK(status IN ('sent','failed','aggregated')),message_preview TEXT,error_message TEXT,aggregated_from INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS model_metrics_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT,snapshot_date DATE NOT NULL,accuracy REAL,precision REAL,recall REAL,f1_score REAL,roc_auc REAL,total_predictions INTEGER,normal_count INTEGER,anomalous_count INTEGER,fpr REAL,note TEXT);
CREATE TABLE IF NOT EXISTS configuration (key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
INSERT OR IGNORE INTO configuration(key,value) VALUES ('block_threshold','0.7'),('notification_enabled','1'),('telegram_bot_token',''),('telegram_chat_id',''),('notification_aggregation_window_sec','60'),('max_notifications_per_hour','20'),('middleware_enabled','1');

-- Spec 05 addendum: akun mahasiswa (student accounts) untuk login sungguhan.
CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,full_name TEXT,student_id TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_students_username ON students(username);

-- Spec 05 addendum: audit trail setiap percobaan login (berhasil/gagal).
CREATE TABLE IF NOT EXISTS login_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,username TEXT,source_ip TEXT,result TEXT NOT NULL CHECK(result IN ('success','invalid_username','invalid_password')),traffic_log_id INTEGER REFERENCES traffic_logs(id));
CREATE INDEX IF NOT EXISTS idx_login_attempts_timestamp ON login_attempts(timestamp);
CREATE INDEX IF NOT EXISTS idx_login_attempts_username ON login_attempts(username);

from typing import Optional
class TrafficLogger:
    def __init__(self, db_conn): self.db=db_conn
    def log_request(self, request:dict,label:str,confidence:float,action:str,latency_ms:float,attack_class:Optional[str]=None):
        h=request.get('headers',{}) or {}
        cur=self.db.execute('''INSERT INTO traffic_logs(source_ip,method,url,full_url,user_agent,referer,content_type,payload_body,label,confidence,attack_class,action,inference_latency_ms,feature_count,is_blocked) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(
            request.get('source_ip'),request.get('method','GET'),request.get('url',''),request.get('url',''),h.get('User-Agent',''),h.get('Referer',''),h.get('Content-Type',''),request.get('body',''),label,float(confidence),attack_class,action,float(latency_ms),request.get('feature_count'),1 if action=='block' else 0))
        self.db.commit(); return cur.lastrowid

    def log_notification(self, traffic_log_id: Optional[int], status: str, message_preview: str = '', error_message: Optional[str] = None, aggregated_from: int = 1):
        """Catat hasil pengiriman notifikasi Telegram (Spec 07)."""
        cur = self.db.execute(
            '''INSERT INTO notification_logs(traffic_log_id, sent_at, status, message_preview, error_message, aggregated_from)
               VALUES(?, CURRENT_TIMESTAMP, ?, ?, ?, ?)''',
            (traffic_log_id, status, (message_preview or '')[:200], error_message, aggregated_from),
        )
        self.db.commit()
        return cur.lastrowid

    def log_login_attempt(self, username: str, source_ip: Optional[str], result: str, traffic_log_id: Optional[int] = None):
        """Catat setiap percobaan login (Spec 05 addendum)."""
        cur = self.db.execute(
            '''INSERT INTO login_attempts(username, source_ip, result, traffic_log_id) VALUES(?, ?, ?, ?)''',
            (username, source_ip, result, traffic_log_id),
        )
        self.db.commit()
        return cur.lastrowid

import os, tempfile, sqlite3
from .connection import init_db, get_connection
from .logger import TrafficLogger
def test_logging():
    old=os.environ.get('AI_GUARD_DB_PATH');
    with tempfile.TemporaryDirectory() as d:
        os.environ['AI_GUARD_DB_PATH']=os.path.join(d,'t.db')
        # module constant is fixed, so test direct connection instead
        c=sqlite3.connect(os.path.join(d,'t.db')); c.executescript(open(os.path.join(os.path.dirname(__file__),'schema.sql')).read())
        TrafficLogger(c).log_request({'method':'GET','url':'/x','headers':{},'body':''},'normal',.9,'allow',1.2)
        assert c.execute('select count(*) from traffic_logs').fetchone()[0]==1
        c.close()
    if old is None: os.environ.pop('AI_GUARD_DB_PATH',None)
    else: os.environ['AI_GUARD_DB_PATH']=old

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Force IPv4 localhost for test DB connections on Windows (port 5433 to avoid host PostgreSQL conflict)
os.environ['DATABASE_URL'] = 'postgresql://agriva_user:agriva_pass@127.0.0.1:5433/agriva_db'

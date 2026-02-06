import streamlit as st
import hashlib
from database import Database

class Authentication:
    def __init__(self):
        self.db = Database()
        
    def hash_password(self, password):
        """Simple password hashing"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self, username, password):
        """Authenticate user"""
        # SQLite uses ? as placeholder, not %s
        query = "SELECT * FROM users WHERE username = ? AND password = ? AND is_active = TRUE"
        hashed_password = self.hash_password(password)
        
        try:
            result = self.db.execute_query(query, (username, hashed_password))
            
            if result and len(result) > 0:
                user = result[0]
                
                # Store authentication in session state
                st.session_state.authenticated = True
                st.session_state.username = user['username']
                st.session_state.role = user['role']
                st.session_state.user_id = user['id']
                
                return {
                    'authenticated': True,
                    'username': user['username'],
                    'role': user['role'],
                    'user_id': user['id']
                }
                
        except Exception as e:
            st.error(f"Database error: {e}")
            return {'authenticated': False, 'error': 'System error'}
        
        # For demo purposes, check default credentials
        if username == 'admin' and password == 'admin123':
            # Store in session state for demo user too
            st.session_state.authenticated = True
            st.session_state.username = 'admin'
            st.session_state.role = 'admin'
            st.session_state.user_id = 1
            
            return {
                'authenticated': True,
                'username': 'admin',
                'role': 'admin',
                'user_id': 1
            }
        
        return {'authenticated': False, 'error': 'Invalid credentials'}
    
    def logout(self):
        """Clear session state - only auth-related keys"""
        auth_keys = ['authenticated', 'username', 'role', 'user_id']
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def check_auth(self):
        """Check if user is authenticated"""
        # CORRECTED: Properly access session state
        return st.session_state.get('authenticated', False)
    
    def require_auth(self):
        """Redirect to login if not authenticated"""
        if not self.check_auth():
            st.error("Please login to access this page")
            st.stop()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import json
import time
from streamlit_option_menu import option_menu
from auth import Authentication
from database import Database
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
# from twilio.rest import Client  # Removed: Add twilio to requirements.txt if needed
import threading

# Page configuration
st.set_page_config(
    page_title="Sales Management System",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with notification styles
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #2563EB;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .card {
        background-color: #F8FAFC;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .success-card {
        background: linear-gradient(135deg, #34D399 0%, #059669 100%);
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #FBBF24 0%, #D97706 100%);
        color: white;
    }
    .danger-card {
        background: linear-gradient(135deg, #F87171 0%, #DC2626 100%);
        color: white;
    }
    .info-card {
        background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%);
        color: white;
    }
    .btn-primary {
        background-color: #3B82F6 !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 5px !important;
    }
    .btn-success {
        background-color: #10B981 !important;
        color: white !important;
    }
    .btn-danger {
        background-color: #EF4444 !important;
        color: white !important;
    }
    .stButton > button {
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .stock-green {
        color: #10B981;
        font-weight: bold;
    }
    .stock-yellow {
        color: #F59E0B;
        font-weight: bold;
    }
    .stock-red {
        color: #EF4444;
        font-weight: bold;
    }
    .receipt-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }
    .receipt-table th, .receipt-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .receipt-table th {
        background-color: #1E3A8A;
        color: white;
        font-weight: bold;
    }
    .receipt-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    .notification-badge {
        position: relative;
        display: inline-block;
    }
    .notification-badge::after {
        content: '🔔';
        position: absolute;
        top: -5px;
        right: -5px;
        font-size: 0.8rem;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .mobile-payment-card {
        background: linear-gradient(135deg, #00B894 0%, #00A085 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .sms-notification {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'selected_module' not in st.session_state:
    st.session_state.selected_module = "Dashboard"
if 'last_receipt' not in st.session_state:
    st.session_state.last_receipt = None
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'notification_count' not in st.session_state:
    st.session_state.notification_count = 0
if 'mobile_payment_config' not in st.session_state:
    st.session_state.mobile_payment_config = {
        'enabled': True,
        'providers': ['M-Pesa', 'Airtel Money', 'T-Kash', 'Equitel'],
        'default_provider': 'M-Pesa'
    }

# Initialize classes
auth = Authentication()
db = Database()

# Notification Manager Class
class NotificationManager:
    def __init__(self):
        self.sms_config = {
            'enabled': False,
            'provider': 'twilio',  # 'twilio' or 'africastalking'
            'twilio_sid': '',
            'twilio_token': '',
            'twilio_number': '',
            'africastalking_username': '',
            'africastalking_api_key': ''
        }
        self.email_config = {
            'enabled': False,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': '',
            'sender_password': '',
            'recipients': []
        }
        
    def send_sms(self, phone_number, message):
        """Send SMS notification"""
        try:
            if not self.sms_config['enabled']:
                return False, "SMS notifications disabled"
                
            if self.sms_config['provider'] == 'twilio' and self.sms_config['twilio_sid']:
                client = Client(self.sms_config['twilio_sid'], 
                              self.sms_config['twilio_token'])
                message = client.messages.create(
                    body=message,
                    from_=self.sms_config['twilio_number'],
                    to=phone_number
                )
                return True, f"SMS sent: {message.sid}"
            elif self.sms_config['provider'] == 'africastalking':
                # Implement Africa's Talking API
                pass
            return False, "SMS configuration incomplete"
        except Exception as e:
            return False, f"SMS error: {str(e)}"
    
    def send_email(self, subject, body, to_email=None):
        """Send email notification"""
        try:
            if not self.email_config['enabled']:
                return False, "Email notifications disabled"
                
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = to_email if to_email else ', '.join(self.email_config['recipients'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], 
                                 self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], 
                        self.email_config['sender_password'])
            server.send_message(msg)
            server.quit()
            
            return True, "Email sent successfully"
        except Exception as e:
            return False, f"Email error: {str(e)}"
    
    def add_notification(self, title, message, notification_type="info"):
        """Add notification to session state"""
        notification = {
            'id': len(st.session_state.notifications) + 1,
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'read': False
        }
        st.session_state.notifications.insert(0, notification)
        st.session_state.notification_count += 1
    
    def check_stock_alerts(self, products):
        """Check for low stock alerts"""
        for product in products:
            if product['stock_quantity'] < product['min_stock_level'] * 0.3:
                # Critical stock
                title = f"🚨 CRITICAL: {product['name']}"
                message = f"{product['name']} has only {product['stock_quantity']} units left (min: {product['min_stock_level']})"
                self.add_notification(title, message, "danger")
                
                # Send external notifications
                if self.email_config['enabled']:
                    self.send_email(
                        f"Critical Stock Alert: {product['name']}",
                        f"Product: {product['name']}\nCurrent Stock: {product['stock_quantity']}\nMinimum Required: {product['min_stock_level']}\nCategory: {product['category']}"
                    )
                
            elif product['stock_quantity'] < product['min_stock_level']:
                # Low stock
                title = f"⚠️ LOW STOCK: {product['name']}"
                message = f"{product['name']} is running low: {product['stock_quantity']} units"
                self.add_notification(title, message, "warning")

# Mobile Payment Processor Class
class MobilePaymentProcessor:
    def __init__(self):
        self.providers = {
            'M-Pesa': {
                'enabled': True,
                'api_url': 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest',
                'consumer_key': '',
                'consumer_secret': '',
                'shortcode': '',
                'passkey': ''
            },
            'Airtel Money': {
                'enabled': True,
                'api_url': 'https://openapi.airtel.africa',
                'client_id': '',
                'client_secret': ''
            },
            'T-Kash': {
                'enabled': True,
                'api_url': 'https://api.t-kash.co.ke',
                'api_key': ''
            },
            'Equitel': {
                'enabled': True,
                'api_url': 'https://equitel.com/api',
                'api_key': ''
            }
        }
    
    def initiate_payment(self, provider, phone_number, amount, reference):
        """Initiate mobile payment"""
        try:
            if provider == 'M-Pesa':
                return self._process_mpesa(phone_number, amount, reference)
            elif provider == 'Airtel Money':
                return self._process_airtel(phone_number, amount, reference)
            elif provider == 'T-Kash':
                return self._process_tkash(phone_number, amount, reference)
            elif provider == 'Equitel':
                return self._process_equitel(phone_number, amount, reference)
            else:
                return False, "Provider not supported"
        except Exception as e:
            return False, f"Payment error: {str(e)}"
    
    def _process_mpesa(self, phone_number, amount, reference):
        """Process M-Pesa payment (simulated)"""
        # In production, implement actual M-Pesa API calls
        # This is a simulation
        st.success(f"📱 M-Pesa payment initiated for KES {amount:,.2f}")
        st.info(f"Check your phone {phone_number} to complete payment")
        
        # Simulate payment confirmation after 3 seconds
        time.sleep(3)
        
        return True, f"MPESA{random.randint(100000, 999999)}"
    
    def _process_airtel(self, phone_number, amount, reference):
        """Process Airtel Money payment (simulated)"""
        st.success(f"📱 Airtel Money payment initiated for KES {amount:,.2f}")
        st.info(f"Check your phone {phone_number} to complete payment")
        time.sleep(3)
        return True, f"AIRTEL{random.randint(100000, 999999)}"
    
    def _process_tkash(self, phone_number, amount, reference):
        """Process T-Kash payment (simulated)"""
        st.success(f"📱 T-Kash payment initiated for KES {amount:,.2f}")
        st.info(f"Check your phone {phone_number} to complete payment")
        time.sleep(3)
        return True, f"TRKASH{random.randint(100000, 999999)}"
    
    def _process_equitel(self, phone_number, amount, reference):
        """Process Equitel payment (simulated)"""
        st.success(f"📱 Equitel payment initiated for KES {amount:,.2f}")
        st.info(f"Check your phone {phone_number} to complete payment")
        time.sleep(3)
        return True, f"EQUITEL{random.randint(100000, 999999)}"

# Initialize managers
notification_manager = NotificationManager()
payment_processor = MobilePaymentProcessor()

# MODULE 1: User Authentication Interface
def show_login():
    st.markdown("<h1 class='main-header'>🔐SALPHINE CHEMOS SALES MANAGEMENT SYSTEM</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown("### Secure Login")
            
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                login_btn = st.button("🚀 Login", type="primary")
            with col_b:
                reset_btn = st.button("🔄 Reset")
            
            if login_btn:
                if username and password:
                    result = auth.login(username, password)
                    if result and result.get('authenticated'):
                        st.session_state.authenticated = True
                        st.session_state.current_user = {
                            'username': result.get('username', 'User'),
                            'role': result.get('role', 'user'),
                            'full_name': result.get('full_name', ''),
                            'email': result.get('email', '')
                        }
                        st.session_state.selected_module = "Dashboard"
                        st.success(f"Welcome, {result.get('username', 'User')}!")
                        
                        # Add login notification
                        notification_manager.add_notification(
                            "👋 Welcome Back!",
                            f"User {username} logged in successfully",
                            "success"
                        )
                        
                        st.rerun()
                    else:
                        error_msg = result.get('error', 'Invalid credentials') if result else 'Login failed'
                        st.error(f"Authentication failed: {error_msg}")
                else:
                    st.warning("Please enter both username and password")
            
            if reset_btn:
                st.rerun()
            
            st.markdown("---")
            st.markdown("""
            **Demo Credentials:**
            - 👑 Admin: `admin` / `admin123`
            - 📊 Manager: `manager1` / `manager123`
            - 💼 Clerk: `clerk1` / `clerk123`
            """)

# QuickSort Algorithm Implementation
def quicksort_products(products, key='name'):
    """QuickSort algorithm for product sorting"""
    if len(products) <= 1:
        return products
    else:
        pivot = products[len(products)//2][key]
        left = [x for x in products if x[key] < pivot]
        middle = [x for x in products if x[key] == pivot]
        right = [x for x in products if x[key] > pivot]
        return quicksort_products(left, key) + middle + quicksort_products(right, key)

# MODULE 2: Dashboard (Enhanced with Notifications)
def show_dashboard():
    st.markdown("<h1 class='main-header'>📊 Dashboard Overview</h1>", unsafe_allow_html=True)
    
    # Notification Bell
    col_notif, col_space = st.columns([1, 10])
    with col_notif:
        if st.session_state.notification_count > 0:
            st.markdown(f'<div class="notification-badge">🔔 {st.session_state.notification_count}</div>', unsafe_allow_html=True)
            if st.button("📨", help="View Notifications"):
                show_notifications_popup()
    
    # Get sample data
    products, users = db.get_sample_data()
    
    # Check for stock alerts
    notification_manager.check_stock_alerts(products)
    
    # Calculate metrics
    total_products = len(products)
    low_stock = sum(1 for p in products if p['stock_quantity'] < p['min_stock_level'])
    critical_stock = sum(1 for p in products if p['stock_quantity'] < p['min_stock_level'] * 0.3)
    total_stock_value = sum(p['price'] * p['stock_quantity'] for p in products)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card info-card'>
            <h3>📦 Total Products</h3>
            <h2>{total_products}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card warning-card'>
            <h3>⚠️ Low Stock Items</h3>
            <h2>{low_stock}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card danger-card'>
            <h3>🚨 Critical Stock</h3>
            <h2>{critical_stock}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='metric-card success-card'>
            <h3>💰 Stock Value</h3>
            <h2>KES {total_stock_value:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent activity and charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Stock Status Distribution")
        
        # Create stock status data
        status_data = {
            'Status': ['Adequate', 'Low Stock', 'Critical'],
            'Count': [
                total_products - low_stock,
                low_stock - critical_stock,
                critical_stock
            ]
        }
        
        fig = px.pie(status_data, values='Count', names='Status', 
                    color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444'])
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        st.markdown("### 📊 Top Products by Stock Value")
        
        # Sort products by stock value
        sorted_products = sorted(products, key=lambda x: x['price'] * x['stock_quantity'], reverse=True)[:8]
        
        data = pd.DataFrame({
            'Product': [p['name'] for p in sorted_products],
            'Value': [p['price'] * p['stock_quantity'] for p in sorted_products]
        })
        
        fig = px.bar(data, x='Product', y='Value', 
                    color='Value',
                    color_continuous_scale='Viridis')
        fig.update_layout(xaxis_title="", yaxis_title="Stock Value (KES)")
        st.plotly_chart(fig, width='stretch')
    
    # Low stock alerts
    st.markdown("### ⚠️ Low Stock Alerts")
    
    low_stock_items = [p for p in products if p['stock_quantity'] < p['min_stock_level']]
    
    if low_stock_items:
        alert_data = []
        for item in low_stock_items:
            alert_level = "CRITICAL" if item['stock_quantity'] < item['min_stock_level'] * 0.3 else "LOW"
            
            alert_data.append({
                'Product': item['name'],
                'Category': item['category'],
                'Current Stock': item['stock_quantity'],
                'Min Required': item['min_stock_level'],
                'Status': alert_level
            })
        
        df_alerts = pd.DataFrame(alert_data)
        st.dataframe(df_alerts, width='stretch', hide_index=True)
        
        # Add SMS/Email notification buttons
        st.markdown("### 🔔 Send Stock Alerts")
        col_sms, col_email = st.columns(2)
        
        with col_sms:
            if st.button("📱 Send SMS Alerts", type="primary"):
                send_stock_alerts_sms(low_stock_items)
        
        with col_email:
            if st.button("📧 Send Email Alerts", type="primary"):
                send_stock_alerts_email(low_stock_items)
    else:
        st.success("🎉 All products have sufficient stock levels!")

def show_notifications_popup():
    """Display notifications popup"""
    with st.expander("📨 Notifications", expanded=True):
        if not st.session_state.notifications:
            st.info("No new notifications")
        else:
            for notification in st.session_state.notifications[:10]:  # Show last 10
                col1, col2, col3 = st.columns([8, 2, 1])
                with col1:
                    if notification['type'] == 'danger':
                        st.error(f"**{notification['title']}**\n{notification['message']}")
                    elif notification['type'] == 'warning':
                        st.warning(f"**{notification['title']}**\n{notification['message']}")
                    elif notification['type'] == 'success':
                        st.success(f"**{notification['title']}**\n{notification['message']}")
                    else:
                        st.info(f"**{notification['title']}**\n{notification['message']}")
                with col2:
                    st.caption(notification['timestamp'])
                with col3:
                    if not notification['read']:
                        if st.button("✓", key=f"read_{notification['id']}"):
                            notification['read'] = True
                            st.session_state.notification_count -= 1
                            st.rerun()
            
            if st.button("Clear All Notifications"):
                st.session_state.notifications = []
                st.session_state.notification_count = 0
                st.rerun()

def send_stock_alerts_sms(low_stock_items):
    """Send SMS alerts for low stock items"""
    # This would require actual SMS gateway configuration
    st.warning("SMS notifications require configuration in Settings > Notifications")
    st.info("Configure Twilio or Africa's Talking API to enable SMS alerts")

def send_stock_alerts_email(low_stock_items):
    """Send email alerts for low stock items"""
    if not notification_manager.email_config['enabled']:
        st.warning("Email notifications are disabled. Enable in Settings > Notifications")
        return
    
    try:
        subject = f"Stock Alert - {datetime.now().strftime('%Y-%m-%d')}"
        body = "Low Stock Items:\n\n"
        for item in low_stock_items:
            status = "CRITICAL" if item['stock_quantity'] < item['min_stock_level'] * 0.3 else "LOW"
            body += f"- {item['name']}: {item['stock_quantity']} units (Min: {item['min_stock_level']}) - {status}\n"
        
        success, message = notification_manager.send_email(subject, body)
        if success:
            st.success("Email alerts sent successfully!")
            notification_manager.add_notification(
                "📧 Email Sent",
                "Low stock alerts emailed to recipients",
                "success"
            )
        else:
            st.error(f"Failed to send email: {message}")
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")

# MODULE 3: Sales Processing Interface (Enhanced with Mobile Payments)
def show_sales_processing():
    st.markdown("<h1 class='main-header'>🛒 Sales Processing</h1>", unsafe_allow_html=True)
    
    products, _ = db.get_sample_data()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🏷️ Product Selection")
        
        # Search and filter
        search_term = st.text_input("🔍 Search products", placeholder="Type product name or category...")
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            categories = list(set(p['category'] for p in products))
            selected_category = st.selectbox("📂 Filter by category", ["All"] + categories)
        
        with col_filter2:
            sort_option = st.selectbox("🔢 Sort by", ["Name (A-Z)", "Name (Z-A)", "Price (Low-High)", "Price (High-Low)"])
        
        # Filter products
        filtered_products = products
        
        if search_term:
            filtered_products = [p for p in filtered_products 
                               if search_term.lower() in p['name'].lower() 
                               or search_term.lower() in p['category'].lower()]
        
        if selected_category != "All":
            filtered_products = [p for p in filtered_products if p['category'] == selected_category]
        
        # Sort using QuickSort
        sort_key_map = {
            "Name (A-Z)": ('name', False),
            "Name (Z-A)": ('name', True),
            "Price (Low-High)": ('price', False),
            "Price (High-Low)": ('price', True)
        }
        
        sort_key, reverse = sort_key_map[sort_option]
        sorted_products = quicksort_products(filtered_products, sort_key)
        if reverse:
            sorted_products = sorted_products[::-1]
        
        # Display products in grid
        st.markdown("### Available Products")
        
        cols = st.columns(3)
        for idx, product in enumerate(sorted_products):
            with cols[idx % 3]:
                with st.container():
                    stock_status = "🟢" if product['stock_quantity'] >= product['min_stock_level'] else \
                                  "🟡" if product['stock_quantity'] >= product['min_stock_level'] * 0.3 else "🔴"
                    
                    st.markdown(f"""
                    <div class='card'>
                        <h4>{stock_status} {product['name']}</h4>
                        <p><strong>Category:</strong> {product['category']}</p>
                        <p><strong>Price:</strong> KES {product['price']:,.2f}</p>
                        <p><strong>Stock:</strong> {product['stock_quantity']} units</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    qty = st.number_input(f"Quantity", min_value=1, max_value=product['stock_quantity'], 
                                         value=1, key=f"qty_{product['id']}")
                    
                    if st.button(f"➕ Add to Cart", key=f"add_{product['id']}"):
                        cart_item = {
                            'id': product['id'],
                            'name': product['name'],
                            'price': product['price'],
                            'quantity': qty,
                            'total': product['price'] * qty
                        }
                        
                        # Check if item already in cart
                        existing_item = next((item for item in st.session_state.cart 
                                            if item['id'] == product['id']), None)
                        
                        if existing_item:
                            existing_item['quantity'] += qty
                            existing_item['total'] = existing_item['price'] * existing_item['quantity']
                        else:
                            st.session_state.cart.append(cart_item)
                        
                        st.success(f"Added {qty} x {product['name']} to cart!")
                        st.rerun()
    
    with col2:
        st.markdown("### 🛍️ Shopping Cart")
        
        if not st.session_state.cart:
            st.info("🛒 Your cart is empty")
        else:
            # Display cart items
            cart_total = 0
            for item in st.session_state.cart:
                col_a, col_b, col_c = st.columns([3, 2, 1])
                with col_a:
                    st.write(f"{item['name']}")
                with col_b:
                    st.write(f"{item['quantity']} x KES {item['price']:,.2f}")
                with col_c:
                    if st.button("❌", key=f"remove_{item['id']}"):
                        st.session_state.cart = [i for i in st.session_state.cart if i['id'] != item['id']]
                        st.rerun()
                
                cart_total += item['total']
            
            st.markdown("---")
            st.markdown(f"**Subtotal:** KES {cart_total:,.2f}")
            
            # Tax calculation
            tax_rate = st.slider("Tax Rate (%)", 0.0, 30.0, 16.0, 0.1)
            tax_amount = cart_total * (tax_rate / 100)
            final_total = cart_total + tax_amount
            
            st.markdown(f"**Tax ({tax_rate}%):** KES {tax_amount:,.2f}")
            st.markdown(f"### **Total: KES {final_total:,.2f}**")
            
            st.markdown("---")
            
            # Payment options - Enhanced with mobile payments
            payment_method = st.selectbox("💳 Payment Method", 
                                         ["Cash", "Credit Card", "M-Pesa", "Airtel Money", "T-Kash", "Equitel", "Debit Card", "Bank Transfer"])
            
            customer_name = st.text_input("👤 Customer Name", placeholder="Enter customer name")
            
            # Mobile payment details if selected
            if payment_method in ["M-Pesa", "Airtel Money", "T-Kash", "Equitel"]:
                st.markdown(f'<div class="mobile-payment-card">📱 {payment_method} Payment</div>', unsafe_allow_html=True)
                phone_number = st.text_input("📱 Phone Number", placeholder="2547XXXXXXXX")
                send_receipt_sms = st.checkbox("📨 Send SMS receipt to customer", value=True)
                
                if st.button(f"Initiate {payment_method} Payment", type="primary"):
                    if phone_number and len(phone_number) >= 10:
                        with st.spinner(f"Initiating {payment_method} payment..."):
                            success, reference = payment_processor.initiate_payment(
                                payment_method, phone_number, final_total, 
                                f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            )
                            
                            if success:
                                st.success(f"✅ {payment_method} payment initiated successfully!")
                                st.info(f"Transaction Reference: {reference}")
                                
                                if send_receipt_sms:
                                    # Send SMS receipt
                                    sms_message = f"Payment of KES {final_total:,.2f} received. Ref: {reference}. Thank you!"
                                    sms_success, sms_msg = notification_manager.send_sms(phone_number, sms_message)
                                    if sms_success:
                                        st.success("📨 SMS receipt sent to customer")
                                
                                # Complete the sale
                                complete_sale(customer_name, payment_method, final_total, reference)
                            else:
                                st.error(f"Payment failed: {reference}")
                    else:
                        st.warning("Please enter a valid phone number")
            else:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Complete Sale", type="primary"):
                        if customer_name:
                            complete_sale(customer_name, payment_method, final_total)
                        else:
                            st.warning("Please enter customer name")
            
                with col_btn2:
                    if st.button("🗑️ Clear Cart", type="secondary"):
                        st.session_state.cart = []
                        st.rerun()
        
        # Show last receipt if exists
        if st.session_state.last_receipt:
            st.markdown("---")
            if st.button("📄 View Last Receipt"):
                show_receipt_preview(st.session_state.last_receipt)

def complete_sale(customer_name, payment_method, final_total, mobile_ref=None):
    """Complete sale and generate receipt"""
    # Generate receipt
    receipt_data = {
        'transaction_id': f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'customer_name': customer_name,
        'items': st.session_state.cart.copy(),
        'subtotal': sum(item['total'] for item in st.session_state.cart),
        'tax_rate': 16.0,  # Default tax
        'tax_amount': sum(item['total'] for item in st.session_state.cart) * 0.16,
        'total': final_total,
        'payment_method': payment_method,
        'mobile_ref': mobile_ref,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'user': st.session_state.current_user['username']
    }
    
    # Save receipt to session
    st.session_state.last_receipt = receipt_data
    
    # Update stock quantities
    products, _ = db.get_sample_data()
    for cart_item in st.session_state.cart:
        for product in products:
            if product['id'] == cart_item['id']:
                product['stock_quantity'] -= cart_item['quantity']
                break
    
    # Clear cart
    st.session_state.cart = []
    
    # Add notification
    notification_manager.add_notification(
        "💰 Sale Completed",
        f"Transaction {receipt_data['transaction_id']} for KES {final_total:,.2f}",
        "success"
    )
    
    # Check stock levels after sale
    notification_manager.check_stock_alerts(products)
    
    st.success(f"✅ Sale completed! Transaction ID: {receipt_data['transaction_id']}")
    st.balloons()
    
    # Show receipt preview
    show_receipt_preview(receipt_data)

# MODULE 10: Enhanced Settings with Notification Configuration
def show_settings():
    st.markdown("<h1 class='main-header'>⚙️ System Settings</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏢 Business Profile", "🧾 Receipt Template", "🔔 Notifications", "📱 Mobile Payments", "🛠️ System Preferences"])
    
    with tab1:
        st.markdown("### Business Information")
        
        with st.form("business_profile_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                business_name = st.text_input("Business Name*", value="Salphine Chemos Getaway Resort")
                tax_id = st.text_input("Tax ID/VAT Number", value="P123456789")
                currency = st.selectbox("Currency", ["KES", "USD", "EUR", "GBP"], index=0)
                tax_rate = st.number_input("Default Tax Rate (%)", value=16.0, min_value=0.0, max_value=30.0, step=0.1)
            
            with col2:
                address = st.text_area("Address", value="P.O. Box 19938 - 00202 KNH Nairobi")
                phone1 = st.text_input("Primary Phone", value="+254 727 680 468")
                phone2 = st.text_input("Secondary Phone", value="+254 736 880 488")
                email = st.text_input("Business Email", value="info@salphinechemos.com")
                website = st.text_input("Website", value="www.salphinechemos.com")
            
            logo_file = st.file_uploader("Upload Business Logo", type=['png', 'jpg', 'jpeg'])
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                save_profile = st.form_submit_button("💾 Save Profile", type="primary")
            with col_btn2:
                cancel_profile = st.form_submit_button("Cancel", type="secondary")
            
            if save_profile:
                st.success("Business profile updated successfully!")
    
    with tab2:
        st.markdown("### Receipt Template Customization")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### Template Preview")
            
            # Live preview of receipt template
            preview_html = """
            <div style="border: 2px dashed #ccc; padding: 20px; border-radius: 10px; background-color: #fff;">
                <div style="text-align: center;">
                    <h3 style="color: #1E3A8A;">[BUSINESS NAME]</h3>
                    <p>[ADDRESS]</p>
                    <p>Tel: [PHONE1] | [PHONE2]</p>
                    <p>Email: [EMAIL] | Website: [WEBSITE]</p>
                    <hr style="border-top: 2px solid #1E3A8A;">
                    <p><strong>Transaction:</strong> [TRANSACTION_ID]</p>
                    <p><strong>Date:</strong> [DATE] | <strong>Cashier:</strong> [USER]</p>
                    <hr>
                </div>
            </div>
            """
            st.markdown(preview_html, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Template Options")
            
            header_size = st.slider("Header Font Size", 12, 24, 16)
            show_logo = st.checkbox("Show Logo", value=True)
            show_footer = st.checkbox("Show Footer Message", value=True)
            footer_message = st.text_area("Footer Message", value="Thank you for your business!")
            
            template_style = st.selectbox("Template Style", 
                                         ["Modern", "Classic", "Minimal", "Professional"])
            
            if st.button("🔄 Update Template", type="primary"):
                st.success("Receipt template updated successfully!")
    
    with tab3:
        st.markdown("### 🔔 Notification Settings")
        
        # SMS Configuration
        st.markdown("#### 📱 SMS Notifications")
        sms_enabled = st.checkbox("Enable SMS Notifications", value=notification_manager.sms_config['enabled'])
        
        if sms_enabled:
            sms_provider = st.selectbox("SMS Provider", ["Twilio", "Africa's Talking", "Custom API"])
            
            if sms_provider == "Twilio":
                col1, col2 = st.columns(2)
                with col1:
                    twilio_sid = st.text_input("Twilio SID", value=notification_manager.sms_config['twilio_sid'])
                    twilio_token = st.text_input("Twilio Token", type="password")
                with col2:
                    twilio_number = st.text_input("Twilio Phone Number", value=notification_manager.sms_config['twilio_number'])
                
                notification_manager.sms_config.update({
                    'provider': 'twilio',
                    'twilio_sid': twilio_sid,
                    'twilio_token': twilio_token,
                    'twilio_number': twilio_number
                })
            
            # Test SMS
            if st.button("Test SMS Notification"):
                test_phone = st.text_input("Test Phone Number", placeholder="2547XXXXXXXX")
                if test_phone:
                    success, message = notification_manager.send_sms(test_phone, "Test SMS from Salphine Chemos Sales System")
                    if success:
                        st.success("Test SMS sent successfully!")
                    else:
                        st.error(f"Failed to send SMS: {message}")
        
        # Email Configuration
        st.markdown("#### 📧 Email Notifications")
        email_enabled = st.checkbox("Enable Email Notifications", value=notification_manager.email_config['enabled'])
        
        if email_enabled:
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input("SMTP Server", value=notification_manager.email_config['smtp_server'])
                smtp_port = st.number_input("SMTP Port", value=notification_manager.email_config['smtp_port'])
                sender_email = st.text_input("Sender Email", value=notification_manager.email_config['sender_email'])
            with col2:
                sender_password = st.text_input("Sender Password", type="password")
                recipients = st.text_area("Notification Recipients (comma-separated)",
                                        value=", ".join(notification_manager.email_config['recipients']))
            
            notification_manager.email_config.update({
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'sender_email': sender_email,
                'sender_password': sender_password,
                'recipients': [r.strip() for r in recipients.split(',')] if recipients else []
            })
            
            # Test Email
            if st.button("Test Email Notification"):
                test_email = st.text_input("Test Email Address", placeholder="test@example.com")
                if test_email:
                    success, message = notification_manager.send_email(
                        "Test Email from Salphine Chemos",
                        "This is a test email notification from the sales management system.",
                        test_email
                    )
                    if success:
                        st.success("Test email sent successfully!")
                    else:
                        st.error(f"Failed to send email: {message}")
        
        # Stock Alert Settings
        st.markdown("#### ⚠️ Stock Alert Settings")
        col_alert1, col_alert2 = st.columns(2)
        
        with col_alert1:
            alert_on_low = st.checkbox("Alert on Low Stock", value=True)
            low_threshold = st.slider("Low Stock Threshold (%)", 30, 100, 50)
            
        with col_alert2:
            alert_on_critical = st.checkbox("Alert on Critical Stock", value=True)
            critical_threshold = st.slider("Critical Stock Threshold (%)", 10, 50, 30)
        
        # Notification Triggers
        st.markdown("#### 🔔 Notification Triggers")
        triggers = st.multiselect(
            "Send notifications for:",
            ["Low Stock", "Critical Stock", "Sale Completed", "New User Registration", "System Errors"],
            default=["Low Stock", "Critical Stock", "Sale Completed"]
        )
        
        if st.button("💾 Save Notification Settings", type="primary"):
            notification_manager.sms_config['enabled'] = sms_enabled
            notification_manager.email_config['enabled'] = email_enabled
            st.success("Notification settings saved successfully!")
    
    with tab4:
        st.markdown("### 📱 Mobile Payment Configuration")
        
        st.info("Configure mobile payment providers for customer transactions")
        
        # Enable/Disable mobile payments
        mobile_enabled = st.checkbox("Enable Mobile Payments", 
                                    value=st.session_state.mobile_payment_config['enabled'])
        
        if mobile_enabled:
            # Provider configurations
            st.markdown("#### Payment Providers")
            
            for provider in payment_processor.providers:
                with st.expander(f"{provider} Configuration", expanded=provider=="M-Pesa"):
                    enabled = st.checkbox(f"Enable {provider}", 
                                         value=payment_processor.providers[provider]['enabled'],
                                         key=f"enable_{provider}")
                    
                    if provider == "M-Pesa":
                        col1, col2 = st.columns(2)
                        with col1:
                            consumer_key = st.text_input("Consumer Key", 
                                                        value=payment_processor.providers[provider]['consumer_key'],
                                                        key=f"key_{provider}")
                            shortcode = st.text_input("Shortcode",
                                                     value=payment_processor.providers[provider]['shortcode'],
                                                     key=f"shortcode_{provider}")
                        with col2:
                            consumer_secret = st.text_input("Consumer Secret", 
                                                           type="password",
                                                           value=payment_processor.providers[provider]['consumer_secret'],
                                                           key=f"secret_{provider}")
                            passkey = st.text_input("Passkey",
                                                   value=payment_processor.providers[provider]['passkey'],
                                                   key=f"passkey_{provider}")
                        
                        payment_processor.providers[provider].update({
                            'consumer_key': consumer_key,
                            'consumer_secret': consumer_secret,
                            'shortcode': shortcode,
                            'passkey': passkey
                        })
                    
                    elif provider == "Airtel Money":
                        client_id = st.text_input("Client ID", 
                                                 value=payment_processor.providers[provider]['client_id'],
                                                 key=f"client_id_{provider}")
                        client_secret = st.text_input("Client Secret", 
                                                     type="password",
                                                     value=payment_processor.providers[provider]['client_secret'],
                                                     key=f"client_secret_{provider}")
                        
                        payment_processor.providers[provider].update({
                            'client_id': client_id,
                            'client_secret': client_secret
                        })
                    
                    else:
                        api_key = st.text_input("API Key", 
                                               type="password",
                                               value=payment_processor.providers[provider]['api_key'],
                                               key=f"api_key_{provider}")
                        payment_processor.providers[provider]['api_key'] = api_key
                    
                    payment_processor.providers[provider]['enabled'] = enabled
            
            # Test mobile payment
            st.markdown("#### Test Mobile Payment")
            col_test1, col_test2, col_test3 = st.columns(3)
            with col_test1:
                test_provider = st.selectbox("Provider", list(payment_processor.providers.keys()))
            with col_test2:
                test_phone = st.text_input("Test Phone", "254712345678")
            with col_test3:
                test_amount = st.number_input("Test Amount (KES)", min_value=1.0, value=10.0)
            
            if st.button("Test Payment", type="primary"):
                with st.spinner(f"Initiating test {test_provider} payment..."):
                    success, reference = payment_processor.initiate_payment(
                        test_provider, test_phone, test_amount, "TEST"
                    )
                    if success:
                        st.success(f"Test payment initiated! Reference: {reference}")
                    else:
                        st.error(f"Test payment failed: {reference}")
        
        if st.button("💾 Save Mobile Payment Settings", type="primary"):
            st.session_state.mobile_payment_config['enabled'] = mobile_enabled
            st.success("Mobile payment settings saved successfully!")
    
    with tab4:  # System Preferences tab remains the same
        # ... [Keep existing System Preferences code]
        pass

# MODULE 9: Main Navigation Sidebar (Enhanced with Notification Badge)
def main_navigation():
    # Only show navigation if authenticated
    if not st.session_state.authenticated:
        return
    
    # Create sidebar navigation
    with st.sidebar:
        st.markdown("""
        <style>
        .sidebar-header {
            font-size: 1.8rem;
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        .user-info {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            text-align: center;
        }
        .notification-sidebar {
            background-color: #FFEAA7;
            padding: 0.5rem;
            border-radius: 5px;
            margin-bottom: 1rem;
            text-align: center;
            cursor: pointer;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # User info with notification badge
        if st.session_state.current_user:
            user_role_icon = {
                'admin': '👑',
                'manager': '📊',
                'clerk': '💼'
            }.get(st.session_state.current_user.get('role', 'user'), '👤')
            
            # Notification badge in sidebar
            if st.session_state.notification_count > 0:
                st.markdown(f"""
                <div class='notification-sidebar' onclick="alert('You have {st.session_state.notification_count} notifications')">
                    🔔 {st.session_state.notification_count} New Notification(s)
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='user-info'>
                <h4>{user_role_icon} {st.session_state.current_user.get('username', 'User')}</h4>
                <p>{st.session_state.current_user.get('role', 'USER').upper()}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<h2 class='sidebar-header'>📋 Navigation</h2>", unsafe_allow_html=True)
        
        # Navigation menu
        selected = option_menu(
            menu_title=None,
            options=["📊 Dashboard", "🛒 Sales", "📦 Inventory", "📈 Reports", "👥 Users", "⚙️ Settings", "🔐 Security", "🚪 Logout"],
            icons=["speedometer2", "cart", "box", "graph-up", "people", "gear", "shield-lock", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#f8f9fa"},
                "icon": {"color": "#1E3A8A", "font-size": "18px"}, 
                "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#e9ecef"},
                "nav-link-selected": {"background-color": "#1E3A8A"},
            }
        )
        
        # Update selected module
        module_map = {
            "📊 Dashboard": "Dashboard",
            "🛒 Sales": "Sales Processing",
            "📦 Inventory": "Inventory",
            "📈 Reports": "Reports",
            "👥 Users": "User Management",
            "⚙️ Settings": "Settings",
            "🔐 Security": "Security",
            "🚪 Logout": "Logout"
        }
        
        st.session_state.selected_module = module_map[selected]
        
        # Quick SMS Compose
        st.markdown("---")
        with st.expander("📱 Quick SMS", expanded=False):
            quick_phone = st.text_input("Phone", placeholder="2547XXXXXXXX")
            quick_message = st.text_area("Message", placeholder="Quick message...")
            if st.button("Send SMS", type="primary"):
                if quick_phone and quick_message:
                    success, msg = notification_manager.send_sms(quick_phone, quick_message)
                    if success:
                        st.success("SMS sent!")
                    else:
                        st.error(f"Failed: {msg}")
        
        # Business info footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; font-size: 0.8rem; color: #666;">
            <p><strong>Salphine chemos Getaway Resort</strong></p>
            <p>P.O. Box 19938 - 00202 KNH Nairobi</p>
            <p>📞 +254 727 680 468</p>
            <p>📧 info@salphinechemos.com</p>
            <p>🌐 www.salphinechemos.com</p>
        </div>
        """, unsafe_allow_html=True)

# Main application flow
def main():
    # Check authentication
    if not st.session_state.authenticated:
        show_login()
    else:
        # Show navigation
        main_navigation()
        
        # Display selected module
        if st.session_state.selected_module == "Dashboard":
            show_dashboard()
        elif st.session_state.selected_module == "Sales Processing":
            show_sales_processing()
        elif st.session_state.selected_module == "Inventory":
            show_inventory()
        elif st.session_state.selected_module == "Reports":
            show_reports()
        elif st.session_state.selected_module == "User Management":
            show_user_management()
        elif st.session_state.selected_module == "Settings":
            show_settings()
        elif st.session_state.selected_module == "Security":
            show_security()
        elif st.session_state.selected_module == "Logout":
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("### 👋 Logout Confirmation")
                st.warning("Are you sure you want to logout?")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Yes, Logout", type="primary"):
                        # Add logout notification
                        notification_manager.add_notification(
                            "👋 User Logged Out",
                            f"User {st.session_state.current_user['username']} logged out",
                            "info"
                        )
                        
                        st.session_state.authenticated = False
                        st.session_state.current_user = None
                        st.session_state.cart = []
                        st.session_state.last_receipt = None
                        st.success("Logged out successfully!")
                        st.rerun()
                with col_btn2:
                    if st.button("❌ Cancel"):
                        st.session_state.selected_module = "Dashboard"
                        st.rerun()

if __name__ == "__main__":
    main()
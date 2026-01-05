import streamlit as st
import pandas as pd
import datetime
import uuid
import time
import google.generativeai as genai

# --- Configuration & Theme ---
st.set_page_config(
    page_title="BookKeepCA",
    page_icon="🍁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Canadian Theme (Red/White/Slate)
st.markdown("""
    <style>
        .main { background-color: #F8FAFC; }
        .stButton>button {
            background-color: #B91C1C;
            color: white;
            border-radius: 8px;
            border: none;
            font-weight: bold;
        }
        .stButton>button:hover { background-color: #991B1B; color: white; }
        h1, h2, h3 { color: #1E293B; }
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .highlight-red { color: #B91C1C; font-weight: bold; }
        .highlight-emerald { color: #059669; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- Constants ---
PROVINCES = [
    "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
    "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island",
    "Quebec", "Saskatchewan", "Yukon"
]

CATEGORIES = [
    "Sales", "Services", "Advertising", "Meals & Entertainment", 
    "Office Supplies", "Rent", "Salaries", "Software", "Travel", 
    "Utilities", "Inventory", "Bank Fees", "GST/HST Paid", "GST/HST Collected", 
    "Owner Draw", "Owner Investment"
]

# --- AI Helper ---
def call_gemini(prompt):
    """
    Calls Google Gemini API.
    Requires 'GEMINI_API_KEY' in .streamlit/secrets.toml
    """
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            return "⚠️ AI features require an API Key in secrets.toml"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Service Unavailable: {str(e)}"

# --- Data Management (Session State Mock DB) ---
# NOTE: Replace this class with firebase_admin logic for production
class DataManager:
    def __init__(self):
        if 'db' not in st.session_state:
            st.session_state.db = {
                'users': {},
                'businesses': {},
                'accounts': [],
                'transactions': []
            }
    
    def get_db(self):
        return st.session_state.db

    def create_business(self, user_email, data):
        bus_id = str(uuid.uuid4())
        self.get_db()['businesses'][bus_id] = {**data, 'owner_email': user_email}
        # Create default accounts
        self.create_account(bus_id, "Main Chequing", "Bank", 0.0)
        self.create_account(bus_id, "Corporate Card", "Credit Card", 0.0)
        return bus_id

    def get_business_by_user(self, email):
        for bid, data in self.get_db()['businesses'].items():
            if data['owner_email'] == email:
                return {'id': bid, **data}
        return None

    def create_account(self, business_id, name, type_, balance):
        acc = {
            'id': str(uuid.uuid4()),
            'business_id': business_id,
            'name': name,
            'type': type_,
            'initial_balance': float(balance),
            'is_active': True
        }
        self.get_db()['accounts'].append(acc)

    def get_accounts(self, business_id):
        return [a for a in self.get_db()['accounts'] if a['business_id'] == business_id]

    def add_transaction(self, business_id, data):
        tx = {
            'id': str(uuid.uuid4()),
            'business_id': business_id,
            'date': datetime.datetime.now(),
            **data
        }
        self.get_db()['transactions'].append(tx)

    def get_transactions(self, business_id):
        return [t for t in self.get_db()['transactions'] if t['business_id'] == business_id]

db = DataManager()

# --- Views ---

def login_view():
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("## 🍁 BookKeepCA")
        st.markdown("# Bookkeeping for Canadian Entrepreneurs.")
        st.markdown("Simple, CRA-compliant financial tracking. Powered by AI.")
        
        st.info("💡 **Tip:** This is a Streamlit port of the React application.")

    with col2:
        with st.container(border=True):
            st.subheader("Sign In")
            email = st.text_input("Email", "demo@business.ca")
            password = st.text_input("Password", type="password")
            
            if st.button("Log In / Start Demo", use_container_width=True):
                st.session_state.user = {'email': email}
                st.session_state.logged_in = True
                st.rerun()

def onboarding_view():
    st.markdown("## 🍁 Let's set up your business")
    st.markdown("We need a few details to configure your CRA tax settings.")
    
    with st.form("onboarding_form"):
        c1, c2 = st.columns(2)
        first_name = c1.text_input("First Name")
        last_name = c2.text_input("Last Name")
        
        bus_name = st.text_input("Legal Business Name", placeholder="e.g. Maple Leaf Consulting Inc.")
        
        c3, c4 = st.columns(2)
        entity_type = c3.selectbox("Entity Type", ["Sole Proprietorship", "Corporation", "Partnership"])
        bn_number = c4.text_input("Business Number (BN)", placeholder="9 digits (Optional)")
        
        st.markdown("### Location")
        c5, c6 = st.columns(2)
        city = c5.text_input("City")
        province = c6.selectbox("Province", PROVINCES, index=8) # Default Ontario
        
        if st.form_submit_button("Launch Dashboard"):
            if bus_name:
                bus_data = {
                    'name': bus_name,
                    'type': entity_type,
                    'bn': bn_number,
                    'city': city,
                    'province': province
                }
                db.create_business(st.session_state.user['email'], bus_data)
                st.rerun()
            else:
                st.error("Business Name is required.")

def dashboard_view(business):
    # Sidebar
    with st.sidebar:
        st.title("🍁 BookKeepCA")
        st.caption(f"Business: {business['name']}")
        st.divider()
        menu = st.radio("Navigation", ["Overview", "Transactions", "Accounts", "Settings"])
        st.divider()
        if st.button("Log Out"):
            st.session_state.clear()
            st.rerun()

    # Data Fetching
    accounts = db.get_accounts(business['id'])
    transactions = db.get_transactions(business['id'])
    
    # Calculate Balances
    acc_balances = {a['id']: a['initial_balance'] for a in accounts}
    for t in transactions:
        amt = float(t['amount'])
        if t['type'] == 'Inflow':
            acc_balances[t['account_id']] += amt
        elif t['type'] == 'Outflow':
            acc_balances[t['account_id']] -= amt
        elif t['type'] == 'Transfer':
            acc_balances[t['from_account_id']] -= amt
            acc_balances[t['to_account_id']] += amt

    # Calculate KPIs
    assets = sum(b for aid, b in acc_balances.items() if any(a['type'] != 'Credit Card' and a['id'] == aid for a in accounts))
    # Note: Logic simplified for demo. Usually Credit Card balance is positive liability.
    liabilities = 0
    for acc in accounts:
        bal = acc_balances[acc['id']]
        if acc['type'] == 'Credit Card':
            liabilities += abs(bal) # Assuming positive balance on CC logic in this app means debt
        elif bal < 0:
            liabilities += abs(bal)
            
    net_position = assets - liabilities

    # --- TABS ---
    
    if menu == "Overview":
        st.header("Financial Dashboard")
        
        # KPI Row
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Assets", f"${assets:,.2f}", delta_color="normal")
        k2.metric("Total Liabilities", f"${liabilities:,.2f}", delta_color="inverse")
        k3.metric("Net Position", f"${net_position:,.2f}")
        
        # AI Analyst
        with st.expander("✨ Ask AI Financial Analyst", expanded=True):
            st.markdown("Get a real-time health check of your business finances.")
            if st.button("Generate Insight"):
                with st.spinner("Analyzing your ledger..."):
                    prompt = f"""
                    Act as a Canadian financial analyst. Analyze this data:
                    Assets: ${assets}, Liabilities: ${liabilities}, Net: ${net_position}.
                    Provide a 2-sentence summary with an encouraging tone.
                    """
                    insight = call_gemini(prompt)
                    st.success(insight)

        # Recent Activity
        st.subheader("Recent Activity")
        if transactions:
            df = pd.DataFrame(transactions)
            # Map account names
            acc_map = {a['id']: a['name'] for a in accounts}
            df['Account'] = df['account_id'].map(acc_map)
            # Display cleanup
            display_df = df[['date', 'description', 'category', 'type', 'amount', 'Account']].sort_values('date', ascending=False)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet.")

    elif menu == "Transactions":
        st.header("General Ledger")
        
        # Add Transaction Form
        with st.expander("➕ Record Transaction", expanded=False):
            with st.form("add_tx"):
                c1, c2, c3 = st.columns(3)
                tx_type = c1.selectbox("Type", ["Outflow", "Inflow", "Transfer"])
                date = c2.date_input("Date", datetime.date.today())
                amount = c3.number_input("Amount ($)", min_value=0.01, step=0.01)
                
                desc = st.text_input("Description", placeholder="e.g. Tim Hortons")
                
                # AI Auto-Categorize Button (Mock in form via session state tricky in streamlit, doing simplified)
                category = st.selectbox("Category", CATEGORIES)
                
                # Accounts Logic
                acc_options = {a['name']: a['id'] for a in accounts}
                account_name = st.selectbox("Account", list(acc_options.keys()))
                
                to_account_name = None
                if tx_type == 'Transfer':
                    to_account_name = st.selectbox("To Account", [n for n in acc_options.keys() if n != account_name])

                if st.form_submit_button("Save Transaction"):
                    tx_data = {
                        'type': tx_type,
                        'amount': amount,
                        'description': desc,
                        'category': "Transfer" if tx_type == 'Transfer' else category,
                        'account_id': acc_options[account_name],
                    }
                    if tx_type == 'Transfer':
                        tx_data['from_account_id'] = acc_options[account_name]
                        tx_data['to_account_id'] = acc_options[to_account_name]
                    
                    db.add_transaction(business['id'], tx_data)
                    st.success("Transaction Saved!")
                    time.sleep(1)
                    st.rerun()

        # Ledger Table
        if transactions:
            search = st.text_input("Search transactions", "")
            df = pd.DataFrame(transactions)
            acc_map = {a['id']: a['name'] for a in accounts}
            df['Account'] = df['account_id'].map(acc_map)
            
            if search:
                df = df[df['description'].str.contains(search, case=False) | df['category'].str.contains(search, case=False)]
            
            st.dataframe(
                df[['date', 'description', 'category', 'type', 'amount', 'Account']], 
                use_container_width=True,
                hide_index=True
            )

    elif menu == "Accounts":
        st.header("Accounts")
        
        # Add Account
        with st.expander("Add New Account"):
            with st.form("new_acc"):
                aname = st.text_input("Name")
                atype = st.selectbox("Type", ["Bank", "Credit Card", "Cash"])
                abal = st.number_input("Opening Balance", step=0.01)
                if st.form_submit_button("Create"):
                    db.create_account(business['id'], aname, atype, abal)
                    st.rerun()

        # Grid View
        cols = st.columns(3)
        for idx, acc in enumerate(accounts):
            bal = acc_balances.get(acc['id'], 0.0)
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="color: #64748B; font-size: 0.9em;">{acc['type']}</div>
                    <div style="font-weight: bold; font-size: 1.2em; margin-bottom: 5px;">{acc['name']}</div>
                    <div style="font-size: 1.5em; font-family: monospace; color: {'#B91C1C' if bal < 0 else '#0F172A'}">
                        ${bal:,.2f}
                    </div>
                </div>
                <div style="margin-bottom: 20px;"></div>
                """, unsafe_allow_html=True)

    elif menu == "Settings":
        st.header("Settings")
        st.info("Settings and Team Management features are currently in development.")
        st.json(business)

# --- Main Logic ---

def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_view()
    else:
        user_email = st.session_state.user['email']
        business = db.get_business_by_user(user_email)
        
        if not business:
            onboarding_view()
        else:
            dashboard_view(business)

if __name__ == "__main__":
    main()
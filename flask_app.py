import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import smtplib, ssl
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
import gspread
import json

# -------------------------------------------------
# Streamlit Page Configuration
# -------------------------------------------------
st.set_page_config(page_title="💰 Community Loan App", layout="wide")
st.title("💰 Community Loan Management App (Google Sheets + Email)")

st.write("""
This app lets community members request loans up to **10,000 Birr**.  
All submissions are automatically saved to **Google Sheets** and emailed to the admin for review.
""")

# -------------------------------------------------
# Configuration (replace with your info)
# -------------------------------------------------
ADMIN_EMAIL = "walfanamegersa3@gmail.com"  # Receiver email
SENDER_EMAIL = "walfanamegersa3@gmail.com"  # Sender Gmail
APP_PASSWORD = st.secrets["email_app_password"]  # Gmail App Password from secrets

SHEET_ID = st.secrets["google_sheet_id"]  # Google Sheet ID (from URL)
GCP_SERVICE_ACCOUNT = json.loads(st.secrets["gcp_service_account"])  # GCP credentials JSON

# -------------------------------------------------
# Google Sheets Connection
# -------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_info(GCP_SERVICE_ACCOUNT, scopes=SCOPES)
client = gspread.authorize(CREDS)
sheet = client.open_by_key(SHEET_ID).sheet1

def save_to_gsheet(data):
    """Append loan request to Google Sheet."""
    sheet.append_row(list(data.values()))
    st.success("✅ Loan record saved to Google Sheet successfully!")

# -------------------------------------------------
# Email Sending Function
# -------------------------------------------------
def send_email(subject, message, to_email):
    """Send loan summary email securely using Gmail SMTP."""
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls(context=context)
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        st.success(f"📧 Loan request info sent to {to_email}")
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Authentication failed — check Gmail App Password.")
    except smtplib.SMTPConnectError:
        st.error("❌ Connection error — check internet or firewall.")
    except Exception as e:
        st.error(f"❌ Email sending failed: {e}")

# -------------------------------------------------
# Loan Request Form
# -------------------------------------------------
st.subheader("📝 Loan Request Form")

with st.form("loan_form"):
    full_name = st.text_input("Full Name")
    national_id = st.text_input("National ID")
    staff_status = st.selectbox("Staff Status", ["Active", "Inactive"])
    monthly_salary = st.number_input("Monthly Salary (Birr)", min_value=0.0)
    loan_amount = st.number_input("Requested Loan Amount (max 10,000 Birr)", min_value=0.0, max_value=10000.0)
    loan_duration_days = st.number_input("Repayment Period (Days)", min_value=1, max_value=60, value=30)

    guarantor_name = st.text_input("Guarantor Full Name")
    guarantor_id = st.text_input("Guarantor ID")
    guarantor_phone = st.text_input("Guarantor Phone (e.g., +2519xxxxxxx)")

    agree_interest = st.checkbox("I agree to 10% interest and penalty for late repayment.")
    submitted = st.form_submit_button("📨 Submit Loan Request")

    if submitted:
        if not all([full_name, national_id, guarantor_name, guarantor_id, guarantor_phone]) or not agree_interest:
            st.error("⚠️ Please fill all required fields and agree to the terms.")
        else:
            interest = loan_amount * 0.10
            total_to_repay = loan_amount + interest
            repayment_date = datetime.now() + timedelta(days=loan_duration_days)

            record = {
                "Name": full_name,
                "National ID": national_id,
                "Staff Status": staff_status,
                "Monthly Salary": monthly_salary,
                "Loan Amount": loan_amount,
                "Interest": interest,
                "Total to Repay": total_to_repay,
                "Repayment Date": repayment_date.strftime("%Y-%m-%d"),
                "Guarantor Name": guarantor_name,
                "Guarantor ID": guarantor_id,
                "Guarantor Phone": guarantor_phone,
                "Submitted Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Save to Google Sheet
            save_to_gsheet(record)

            # Send Email
            email_message = f"""
✅ Loan Request Submitted Successfully!

{pd.Series(record).to_string()}
"""
            send_email("✅ New Loan Request Submitted", email_message, ADMIN_EMAIL)

            # Display Summary
            st.success("✅ Loan request submitted successfully!")
            st.write("### Loan Summary:")
            st.json(record)

# -------------------------------------------------
# Display Google Sheet Data
# -------------------------------------------------
st.divider()
st.subheader("📊 All Loan Requests (from Google Sheet)")

try:
    data = sheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df)
    else:
        st.info("No records found yet.")
except Exception as e:
    st.warning(f"⚠️ Could not load data from Google Sheets: {e}")

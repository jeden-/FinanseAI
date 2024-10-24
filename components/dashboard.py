import streamlit as st
import plotly.express as px
from models.transaction import Transaction
from utils.helpers import prepare_transaction_data, calculate_monthly_totals, format_currency
import logging

logger = logging.getLogger(__name__)

def render_dashboard():
    st.subheader("Financial Dashboard")
    
    try:
        transaction_model = Transaction()
        transactions = transaction_model.get_all_transactions()
        
        if not transactions:
            st.info("No transactions found. Start by adding some transactions!")
            return
        
        df = prepare_transaction_data(transactions)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_income = df[df['type'] == 'income']['amount'].sum()
            st.metric("Total Income", format_currency(total_income))
        
        with col2:
            total_expenses = df[df['type'] == 'expense']['amount'].sum()
            st.metric("Total Expenses", format_currency(total_expenses))
        
        with col3:
            balance = total_income - total_expenses
            st.metric("Current Balance", format_currency(balance))
        
        # Category breakdown
        st.subheader("Spending by Category")
        category_data = df[df['type'] == 'expense'].groupby('category')['amount'].sum()
        fig = px.pie(values=category_data.values, names=category_data.index)
        st.plotly_chart(fig)
        
        # Monthly trend
        st.subheader("Monthly Transaction Trend")
        monthly_data = calculate_monthly_totals(df)
        fig = px.line(x=list(monthly_data.keys()), y=list(monthly_data.values()))
        fig.update_layout(yaxis_title="Amount (PLN)")
        st.plotly_chart(fig)
        
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        st.error("An error occurred while loading the dashboard. Please try again later or contact support if the problem persists.")

import pandas as pd

def format_currency(amount):
    return f"{amount:,.2f} PLN"

def prepare_transaction_data(transactions):
    df = pd.DataFrame(transactions)
    df['created_at'] = pd.to_datetime(df['created_at'])
    return df

def calculate_monthly_totals(df):
    monthly = df.set_index('created_at').resample('M')['amount'].sum()
    return monthly.to_dict()

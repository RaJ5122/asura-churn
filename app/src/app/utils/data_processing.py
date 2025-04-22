import pandas as pd

def analyze_data(df):
    # Perform data analysis
    df['Join_Date'] = pd.to_datetime(df['Join_Date'])
    df['Month'] = df['Join_Date'].dt.to_period('M')
    return df

def generate_insights(df):
    insights = {
        'total_customers': len(df),
        'churn_rate': df['Churn'].mean(),
        'avg_monthly_bill': df['Monthly_Bill'].mean()
    }
    return insights
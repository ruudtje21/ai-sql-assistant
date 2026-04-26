import streamlit as st
import sqlite3
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()

with open(".streamlit/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

openai_key = os.getenv("OPENAI_API_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_sql_from_question(question):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system", 
                "content": (
                    "You are an assistant that converts natural language questions into SQL queries. "
                    "Only use the tables and columns that exist in this SQLite schema:"
                    "TABLE customers(CustomerID, Name, City, Email);"
                    "TABLE products(ProductID, ProductName, Category, Price);"
                    "TABLE orders(OrderID, CustomerID, ProductID, OrderDate, Quantity, Total);"
                    "Return SQL only, no explanation."
                )
            },
            {
                "role": "user", "content": question}
        ]
    )
    sql_query = response.choices[0].message.content

    sql_query = sql_query.strip()
    if "```" in sql_query:
        parts = sql_query.split("```")
        if len(parts) >= 2:
            inner = parts[1].lstrip()
            if inner.lower().startswith("sql"):
                inner = inner[3:].lstrip()
            sql_query = inner.strip()
    return sql_query

def is_safe_sql(query):
    unsafe_keywords = ["DROP","DELETE","UPDATE","INSERT","ALTER","CREATE"]
    upper_query = query.upper()

    return not any(keyword in upper_query for keyword in unsafe_keywords)

def run_sql_query(query):
    connection = sqlite3.connect("sample_database.db")
    cursor = connection.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        connection.close()
        return results, columns
    
    except Exception as e:
        connection.close()
        return None, f"SQL error: {str(e)}"
    

st.set_page_config(page_title="AI SQL Assistant")

st.title("AI SQL Assistant")
st.write("Ask a question in plain English, and I'll help you turn it into SQL.")

with st.form("user_question_form"):
    user_question = st.text_input("What would you like to know about your data?")

    submitted = st.form_submit_button("Generate SQL")

if submitted:
    sql = generate_sql_from_question(user_question)
    st.subheader("Generate SQL")
    st.code(sql, language="sql")

    if not is_safe_sql(sql):
        st.error("The generated SQL looks unsafe to run. Please try rephrasing your question.")
        st.stop()

    results, columns_or_error = run_sql_query(sql)

    st.subheader('Results')

    if results is None:
        st.error(f"Error running SQL: {columns_or_error}")
    else:
        st.dataframe(
            {columns_or_error[1]: [row[1] for row in results] for i in range(len(columns_or_error))}
        )
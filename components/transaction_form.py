import streamlit as st
from datetime import datetime
from services.ollama_service import OllamaService
from models.transaction import Transaction
from utils.helpers import format_currency
import logging

logger = logging.getLogger(__name__)

def render_transaction_form():
    st.subheader("New Transaction")
    
    # Add clear instructions for Ollama setup
    st.markdown('''
    ### How to use:
    1. First, open a terminal and run: `ollama run mistral`
    2. Keep that terminal window open
    3. Then enter your transaction below
    ''')
    
    # Check Ollama connection status
    ollama = OllamaService()
    if ollama._check_ollama_running():
        st.success("✅ Connected to Ollama")
    else:
        st.error("❌ Ollama not connected. Please run 'ollama run mistral' in a terminal")
    
    # Example transaction placeholder
    st.markdown("""
    💡 **Example formats:**
    - "internet domowy 20zł miesięcznie"
    - "wypłata 5000 złotych"
    - "czynsz 1500 PLN"
    """)
    
    description = st.text_input(
        "Transaction Description (include amount in PLN/zł)",
        help="Enter transaction description including the amount in Polish currency format (e.g., 20zł, 100 PLN, 50 złotych)"
    )
    
    if st.button("Analyze Transaction"):
        # Create placeholders for status messages and progress
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        result_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        def update_status(message):
            # Determine progress based on message content
            if "Initializing" in message:
                progress = 0.1
                status_placeholder.info(f"🔄 {message}")
            elif "Trying model" in message:
                progress = 0.3
                status_placeholder.warning(f"🤖 {message}")
            elif "not available" in message:
                progress = 0.4
                status_placeholder.warning(f"⚠️ {message}")
            elif "processing" in message:
                progress = 0.6
                status_placeholder.info(f"⚙️ {message}")
            elif "Successfully processed" in message:
                progress = 1.0
                status_placeholder.success(f"✅ {message}")
            else:
                progress = 0.5
                status_placeholder.info(f"ℹ️ {message}")
            
            progress_bar.progress(progress)
        
        update_status("Initializing AI analysis...")
        
        try:
            classification = ollama.classify_transaction(description, status_callback=update_status)
            
            if classification is None:
                status_placeholder.error("""
                ⚠️ Could not process the transaction. Please ensure:
                1. Ollama is installed and running
                2. At least one of these models is available:
                   - mistral (recommended)
                   - llama2:13b
                   - neural-chat
                   - llama2
                3. Run 'ollama pull <model_name>' to install a model
                4. Try again after the model is installed
                """)
                progress_bar.progress(0)
                return
            
            if 'amount' in classification and classification['amount']:
                st.session_state.classification = classification
                result_placeholder.success(f"""
                ✅ Transaction analyzed successfully!
                - Type: {classification['type']}
                - Category: {classification['category']}
                - Amount: {format_currency(classification['amount'])}
                - Cycle: {classification['cycle']}
                """)
            else:
                status_placeholder.warning("""
                ⚠️ Could not detect amount in the description.
                Please include the amount in PLN or zł format, for example:
                - 20zł
                - 100 PLN
                - 50 złotych
                """)
                progress_bar.progress(0)
        except Exception as e:
            logger.error(f"Error during transaction analysis: {str(e)}")
            status_placeholder.error(f"❌ An error occurred while analyzing the transaction: {str(e)}")
            progress_bar.progress(0)
    
    if 'classification' in st.session_state:
        class_data = st.session_state.classification
        
        st.write("### Detected Transaction Details")
        
        # Show and allow editing of extracted amount
        detected_amount = class_data.get('amount', 0)
        amount = st.number_input(
            "Amount (detected from description)",
            value=float(detected_amount),
            min_value=0.01,
            step=0.01,
            help="You can adjust the amount if it wasn't detected correctly"
        )
        
        type = st.selectbox("Type", ["income", "expense"], 
                           index=0 if class_data['type'] == 'income' else 1)
        category = st.text_input("Category", value=class_data['category'])
        cycle = st.selectbox("Cycle", ["none", "daily", "weekly", "monthly", "yearly"],
                           index=["none", "daily", "weekly", "monthly", "yearly"].index(class_data['cycle']))
        
        if cycle != "none":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime.now())
            with col2:
                end_date = st.date_input("End Date", datetime.now())
        else:
            start_date = None
            end_date = None
        
        if st.button("Save Transaction"):
            transaction = Transaction()
            try:
                transaction.create_transaction(
                    description=description,
                    amount=amount,
                    type=type,
                    category=category,
                    cycle=cycle,
                    start_date=start_date,
                    end_date=end_date
                )
                st.success("✅ Transaction saved successfully!")
                st.session_state.pop('classification', None)
                
                # Show summary of saved transaction
                st.write("### Transaction Summary")
                st.write(f"- Description: {description}")
                st.write(f"- Amount: {format_currency(amount)}")
                st.write(f"- Type: {type}")
                st.write(f"- Category: {category}")
                st.write(f"- Cycle: {cycle}")
                if cycle != "none":
                    st.write(f"- Start Date: {start_date}")
                    st.write(f"- End Date: {end_date}")
                
            except Exception as e:
                logger.error(f"Error saving transaction: {str(e)}")
                st.error(f"❌ Error saving transaction: {str(e)}")

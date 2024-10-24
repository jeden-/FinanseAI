import requests
import json
import re
import logging
import time
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, max_retries: int = 5, retry_delay: int = 5):
        self.base_url = "http://localhost:11434/api/generate"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.models_to_try = [
            "mistral",
            "llama2:13b",
            "neural-chat",
            "llama2"
        ]
        
    def _check_ollama_running(self) -> bool:
        """Check if Ollama service is running."""
        try:
            # First try a simple GET request to check if service is up
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _check_model_available(self, model: str) -> bool:
        """Check if specific model is available."""
        try:
            logger.debug(f"Checking availability of model: {model}")
            response = requests.get(f"http://localhost:11434/api/show?name={model}", timeout=5)
            available = response.status_code == 200
            logger.debug(f"Model {model} available: {available}")
            return available
        except Exception as e:
            logger.warning(f"Failed to check model {model} availability: {str(e)}")
            return False

    def _get_model_install_instructions(self, model: str) -> str:
        """Get installation instructions for a specific model."""
        return f"""
To install the {model} model:
1. Open a terminal
2. Run: ollama pull {model}
3. Then run: ollama run {model}
"""

    def classify_transaction(self, description: str, status_callback=None) -> Optional[Dict[str, Any]]:
        """Classify a transaction description using Ollama."""
        logger.info(f"Processing transaction: {description}")
        
        # Check if Ollama is running and wait if needed
        logger.debug("Checking if Ollama service is running...")
        if not self._check_ollama_running():
            logger.warning("Ollama service not running initially")
            if status_callback:
                status_callback("🔄 Waiting for Ollama service to start...")
            time.sleep(2)
            if not self._check_ollama_running():
                error_msg = "Ollama service is not responding. Please ensure:\n" \
                           "1. Ollama is installed\n" \
                           "2. Run 'ollama run mistral' in a terminal\n" \
                           "3. Keep the terminal window open"
                logger.error(error_msg)
                raise ConnectionError(error_msg)
        
        prompt = f"""
        Analyze this Polish transaction description and return a JSON with:
        - type: "income" or "expense"
        - cycle: "none", "daily", "weekly", "monthly", or "yearly"
        - category: appropriate category for the transaction
        - amount: extract the amount in PLN from the description
          (look for formats like: X PLN, X zł, X złotych, X zl, X zlotych, where X is the number)

        Transaction: {description}
        
        Example inputs and outputs:
        Input: "internet domowy 20zł miesięcznie"
        Output: {{"type": "expense", "cycle": "monthly", "category": "utilities", "amount": 20.00}}
        
        Input: "wypłata 5000 złotych"
        Output: {{"type": "income", "cycle": "monthly", "category": "salary", "amount": 5000.00}}
        
        Return only the JSON, no other text.
        """
        
        logger.debug(f"Using prompt template:\n{prompt}")
        
        def make_request():
            for model in self.models_to_try:
                logger.info(f"Attempting request with model: {model}")
                try:
                    response = requests.post(
                        self.base_url,
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=30  # Increased timeout
                    )
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.warning(f"Request failed with status {response.status_code}")
                except Exception as e:
                    logger.warning(f"Request failed: {str(e)}")
                    continue
            return None

        try:
            result = self._retry_connection(make_request)
            if result:
                try:
                    classified = json.loads(result['response'])
                    logger.info(f"Successfully classified: {classified}")
                    
                    # Fallback amount extraction if AI doesn't detect it
                    if 'amount' not in classified or not classified['amount']:
                        amount = self._extract_amount(description)
                        if amount is not None:
                            classified['amount'] = amount
                            logger.debug(f"Amount extracted using fallback: {amount}")
                    
                    return classified
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response: {e}")
                    return None
            return None
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                raise ConnectionError(
                    "Could not connect to Ollama. Please ensure:\n"
                    "1. Ollama is installed\n"
                    "2. Run 'ollama run mistral' in a terminal\n"
                    "3. Keep the terminal window open"
                )
            raise
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text using regex patterns."""
        patterns = [
            r'(\d+(?:[.,]\d{1,2})?)\s*(?:PLN|zł|złotych|zl|zlotych)',  # With currency
            r'(\d+(?:[.,]\d{1,2})?)',  # Just numbers
        ]
        
        logger.debug(f"Attempting to extract amount from: {text}")
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '.')
                    amount = float(amount_str)
                    logger.debug(f"Successfully extracted amount: {amount} using pattern: {pattern}")
                    return amount
                except ValueError as e:
                    logger.warning(f"Failed to convert matched amount: {match.group(1)}, error: {e}")
                    continue
        
        logger.warning("No amount could be extracted from the text")
        return None

    def _retry_connection(self, func) -> Optional[Dict[str, Any]]:
        """Retry mechanism for Ollama API calls."""
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                if not self._check_ollama_running():
                    raise ConnectionError("Ollama service is not running")
                result = func()
                if result:
                    return result
                retries += 1
                logger.warning(f"Attempt {retries}/{self.max_retries} failed to get valid response")
            except Exception as e:
                last_error = e
                logger.error(f"Attempt {retries + 1}/{self.max_retries} failed: {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)

        error_msg = f"Failed after {self.max_retries} attempts. Last error: {str(last_error)}"
        if isinstance(last_error, ConnectionError):
            error_msg += "\nPlease ensure:\n" \
                        "1. Ollama is installed\n" \
                        "2. Run 'ollama run mistral' in a terminal\n" \
                        "3. Keep the terminal window open"
        logger.error(error_msg)
        return None

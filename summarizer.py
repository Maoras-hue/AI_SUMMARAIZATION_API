# summarizer.py
import time
from threading import Lock
from transformers import pipeline

class TextSummarizer:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.model_name = "facebook/bart-large-cnn"
        self._initialized = True
    
    def load_model(self):
        """Lazy load the model"""
        if self.model is None:
            print(f"Loading {self.model_name} model...")
            self.model = pipeline(
                "summarization",
                model=self.model_name,
                device=-1  # Use CPU for free tier
            )
            print("Model loaded successfully!")
        return self.model
    
    def summarize(self, text, max_length=130, min_length=30, do_sample=False):
        """
        Summarize text and return results with metadata
        """
        start_time = time.time()
        
        try:
            model = self.load_model()
            
            # Truncate input if too long (BART has 1024 token limit)
            max_input_length = 1024
            words = text.split()
            if len(words) > max_input_length:
                text = ' '.join(words[:max_input_length])
            
            # Generate summary
            summary = model(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=do_sample
            )[0]['summary_text']
            
            processing_time = time.time() - start_time
            
            # Calculate approximate tokens processed
            input_tokens = len(text.split())
            output_tokens = len(summary.split())
            
            return {
                'success': True,
                'summary': summary,
                'metadata': {
                    'input_length': len(text),
                    'output_length': len(summary),
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'processing_time': processing_time,
                    'model': self.model_name
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }

# Create global summarizer instance
summarizer = TextSummarizer()
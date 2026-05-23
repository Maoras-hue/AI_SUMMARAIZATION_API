# summarizer.py
import time
from threading import Lock

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
        self._initialized = True
    
    def load_model(self):
        if self.model is None:
            print("Loading summarization model...")
            try:
                from transformers import pipeline
                self.model = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
                print("Model loaded!")
            except Exception as e:
                print(f"Model load error: {e}")
                raise
        return self.model
    
    def summarize(self, text, max_length=130, min_length=30, do_sample=False):
        start_time = time.time()
        try:
            model = self.load_model()
            words = text.split()
            if len(words) > 512:
                text = ' '.join(words[:512])
            
            summary = model(text, max_length=max_length, min_length=min_length, do_sample=do_sample)[0]['summary_text']
            
            return {
                'success': True,
                'summary': summary,
                'metadata': {
                    'input_length': len(text),
                    'output_length': len(summary),
                    'processing_time': time.time() - start_time
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

summarizer = TextSummarizer()
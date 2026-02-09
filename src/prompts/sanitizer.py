import re
from typing import Tuple, List
from .vocabulary import FORBIDDEN_TERMS, HARD_LOCK_INJECTION
from .models import SanitizerReport

class PromptSanitizer:
    def __init__(self):
        pass

    def clean(self, text: str, amber_allowed: bool) -> Tuple[str, SanitizerReport]:
        """
        Main sanitization pipeline.
        Returns cleaned text and a full report.
        """
        original_text = text
        blocked_terms = []
        rewrites = False
        
        # 1. Forbidden Terms Check
        cleaned_text = text
        for term in FORBIDDEN_TERMS:
            # Fuzzy/Case-insensitive matching
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            if pattern.search(cleaned_text):
                blocked_terms.append(term)
                cleaned_text = pattern.sub("", cleaned_text) # Simple removal rewrite
                rewrites = True
        
        # 2. Amber Enforcement
        if not amber_allowed:
            # Block amber/orange/tungsten if not allowed
            amber_terms = ["amber", "orange", "tungsten", "warm light", "gold"]
            for term in amber_terms:
                 pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                 if pattern.search(cleaned_text):
                     blocked_terms.append(f"{term} (amber-rule)")
                     cleaned_text = pattern.sub("neutral light", cleaned_text)
                     rewrites = True
        else:
             # If allowed, ensure NO sparks/fire
             fire_terms = ["sparks", "fire", "particles", "flame", "explosion"]
             for term in fire_terms:
                 pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                 if pattern.search(cleaned_text):
                     blocked_terms.append(f"{term} (fire-rule)")
                     cleaned_text = pattern.sub("", cleaned_text)
                     rewrites = True

        # 3. Closed System Enforcement
        # Already handled via FORBIDDEN_TERMS (spill, leak etc)
        
        # 4. One Idea Enforcement
        final_text, one_idea_rewrite = self.enforce_one_idea(cleaned_text)
        if one_idea_rewrite:
            rewrites = True
            
        # 5. Injection (Hard Lock)
        # ALWAYS append mandatory safety tokens. No heuristics.
        # 5. Injection (Hard Lock - Robust Token Check)
        # Ensure mandatory safety tokens are present individually.
        safety_tokens = [t.strip() for t in HARD_LOCK_INJECTION.split(',')]
        
        current_lower = final_text.lower()
        added_tokens = []
        
        for token in safety_tokens:
            # Simple check: is this token phrase present?
            if token.lower() not in current_lower:
                added_tokens.append(token)
                
        if added_tokens:
             injection_str = ", ".join(added_tokens)
             final_text = f"{final_text}, {injection_str}"
             rewrites = True

        # Normalize spaces
        final_text = re.sub(r'\s+', ' ', final_text).strip()
        final_text = re.sub(r',\s*,', ',', final_text) # Fix double commas
        
        report = SanitizerReport(
            blocked_terms_found=blocked_terms,
            rewrites_applied=rewrites
        )
        
        return final_text, report

    def enforce_one_idea(self, text: str) -> Tuple[str, bool]:
        """
        Splits complex sentences. Returns (text, was_changed).
        """
        splitters = [" and then ", ". Then ", " while ", " as ", " before ", " after ", " but "]
        original = text
        
        for s in splitters:
             # Case insensitive check
             if re.search(re.escape(s), text, re.IGNORECASE):
                # Take first part
                text = re.split(re.escape(s), text, flags=re.IGNORECASE)[0]
                
        was_changed = (len(text) != len(original))
        return text.strip(), was_changed

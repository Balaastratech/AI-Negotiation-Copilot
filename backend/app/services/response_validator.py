"""
Response Validator for Gemini AI Responses
Ensures the AI follows the negotiation commander rules
"""
import logging
import re

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates AI responses against negotiation commander rules"""
    
    # Allowed first words for responses
    ALLOWED_FIRST_WORDS = [
        "Ask", "Say", "Tell", "Counter", "Offer", "Walk", "Stay", "Push", "$"
    ]
    
    # Forbidden first words
    FORBIDDEN_FIRST_WORDS = [
        "Given", "You", "The", "It", "Well", "Since", "Maybe", "If", 
        "I think", "I would", "I suggest", "Are", "Do you", "What", 
        "Should", "Would", "Could", "Can you"
    ]
    
    @staticmethod
    def validate_response(text: str) -> dict:
        """
        Validate an AI response against the rules.
        
        Args:
            text: The AI's response text
            
        Returns:
            dict with:
                - valid: bool
                - violations: list of violation codes
                - correction_prompt: str (if violations found)
        """
        if not text or not text.strip():
            return {"valid": True, "violations": [], "correction_prompt": None}
        
        text = text.strip()
        violations = []
        
        # Rule 1: Check if ends with question mark
        if text.endswith('?'):
            violations.append("ENDS_WITH_QUESTION")
        
        # Rule 2: Check for forbidden first words
        first_words = text.split()[:3]  # Check first 3 words for phrases
        first_word = first_words[0] if first_words else ""
        
        # Check single word
        if first_word in ResponseValidator.FORBIDDEN_FIRST_WORDS:
            violations.append(f"FORBIDDEN_START:{first_word}")
        
        # Check two-word phrases
        if len(first_words) >= 2:
            two_word = f"{first_words[0]} {first_words[1]}"
            if two_word in ResponseValidator.FORBIDDEN_FIRST_WORDS:
                violations.append(f"FORBIDDEN_START:{two_word}")
        
        # Rule 3: Check if starts with allowed action word
        starts_with_allowed = any(
            text.startswith(word) for word in ResponseValidator.ALLOWED_FIRST_WORDS
        )
        if not starts_with_allowed and not violations:
            violations.append(f"MISSING_ACTION_START")
        
        # Rule 4: Check for vague language
        vague_patterns = [
            r'\byou could\b',
            r'\byou might\b',
            r'\bconsider\b',
            r'\bmaybe\b',
            r'\bperhaps\b',
            r'\bone option\b',
            r'\ba few options\b'
        ]
        for pattern in vague_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append("VAGUE_LANGUAGE")
                break
        
        # Rule 5: Check for multiple questions in text
        question_count = text.count('?')
        if question_count > 0:
            violations.append(f"CONTAINS_QUESTIONS:{question_count}")
        
        # Generate correction prompt if violations found
        correction_prompt = None
        if violations:
            correction_prompt = ResponseValidator._generate_correction(violations, text)
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "correction_prompt": correction_prompt
        }
    
    @staticmethod
    def _generate_correction(violations: list, original_text: str) -> str:
        """Generate a correction prompt based on violations"""
        
        violation_messages = []
        
        for violation in violations:
            if violation == "ENDS_WITH_QUESTION":
                violation_messages.append("You ended with a question mark")
            elif violation.startswith("FORBIDDEN_START:"):
                word = violation.split(":", 1)[1]
                violation_messages.append(f"You started with forbidden word '{word}'")
            elif violation == "MISSING_ACTION_START":
                violation_messages.append("You must start with: Ask/Say/Counter/Tell/Push/Walk/Stay/Offer")
            elif violation == "VAGUE_LANGUAGE":
                violation_messages.append("You used vague language like 'you could' or 'consider'")
            elif violation.startswith("CONTAINS_QUESTIONS:"):
                violation_messages.append("You asked questions")
        
        correction = (
            f"STOP. Rule violations: {', '.join(violation_messages)}. "
            f"Respond again following ALL rules. "
            f"Start with an action word. End with a command, not a question."
        )
        
        return correction
    
    @staticmethod
    def should_send_correction(violations: list) -> bool:
        """
        Determine if we should send a correction to the AI.
        Some violations are critical, others are minor.
        """
        critical_violations = [
            "ENDS_WITH_QUESTION",
            "CONTAINS_QUESTIONS",
        ]
        
        # Check if any critical violation exists
        for violation in violations:
            if violation in critical_violations:
                return True
            if violation.startswith("FORBIDDEN_START:"):
                return True
        
        return False

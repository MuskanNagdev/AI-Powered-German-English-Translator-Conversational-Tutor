import unittest
import sys
import os

# Add parent directory to path to import routes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.api import refine_tutor_response, normalize_text, is_same_content

class TestTutorLogic(unittest.TestCase):
    
    def test_normalize_text(self):
        """Test that punctuation is removed and text is lowercased"""
        self.assertEqual(normalize_text("Hello, World!"), "hello world")
        self.assertEqual(normalize_text("Woher kommen Sie?"), "woher kommen sie")
        self.assertEqual(normalize_text("   Spaced   Out   "), "spaced   out")
        
    def test_is_same_content(self):
        """Test content equality ignoring case and punctuation"""
        self.assertTrue(is_same_content("Hallo", "hallo!"))
        self.assertTrue(is_same_content("Ich bin gut.", "ich bin gut"))
        self.assertFalse(is_same_content("Ich bin gut", "Du bist gut"))

    def test_refine_response_punctuation_filter(self):
        """Test that pure punctuation corrections are rejected"""
        
        # Scenario: Tutor corrects "comma placement" only
        raw_response = {
            "german_response": "Du meinst: Ich habe Hunger.",
            "english_translation": "You mean: I am hungry.",
            "has_error": True, 
            "correction": "Add a period at the end."
        }
        user_message = "ich habe hunger"
        
        refined = refine_tutor_response(raw_response, user_message)
        
        self.assertFalse(refined['has_error'], "Should override error for punctuation only")
        self.assertIsNone(refined['correction'])
        
    def test_refine_response_grammar_allowed(self):
        """Test that legitimate grammar corrections are KEPT"""
        
        # Scenario: Verb position error
        raw_response = {
            "german_response": "Du meinst: Ich gehe nach Hause.",
            "english_translation": "You mean: I go home.",
            "has_error": True,
            "correction": "Verb 'gehe' must be in second position."
        }
        user_message = "Ich nach Hause gehe"
        
        refined = refine_tutor_response(raw_response, user_message)
        
        self.assertTrue(refined['has_error'], "Should keep error for grammar issues")
        self.assertEqual(refined['correction'], "Verb 'gehe' must be in second position.")

    def test_refine_response_hallucination_filter(self):
        """Test that identical content (hallucinated error) is rejected"""
        
        # Scenario: Tutor corrects capitalization but claims it's an error
        # User says: "woher kommen sie"
        # Tutor says: "Du meinst: Woher kommen Sie?" (Content is same, just caps)
        
        raw_response = {
            "german_response": "Du meinst: Woher kommen Sie?",
            "english_translation": "Where do you come from?",
            "has_error": True,
            "correction": "Subject-verb agreement error" # Hallucinated reason
        }
        user_message = "woher kommen sie"
        
        refined = refine_tutor_response(raw_response, user_message)
        
        self.assertFalse(refined['has_error'], "Should reject error if content is identical")
        self.assertIn("Genau!", refined['german_response'])

if __name__ == '__main__':
    unittest.main()

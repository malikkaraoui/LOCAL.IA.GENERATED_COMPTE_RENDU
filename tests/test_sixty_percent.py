"""Tests finaux pour atteindre strictement >60%."""

import pytest
from pathlib import Path  
from core.context import tokenize, normalize_text, chunk_text
from core.extract import sha256_text, normalize_text as extract_normalize
from core.generate import sanitize_output, truncate_chars, truncate_lines
from core.render import _norm, _stringify_answer, build_moustache_mapping


class TestForSixtyPercent:
    """Tests ciblés pour dépasser 60%."""

    def test_tokenize_comprehensive(self):
        """Tokenize - cas massifs."""
        # Avec stop words
        text1 = "le chat et le chien sont dans la maison avec le chat"
        result1 = tokenize(text1, remove_stop=True)
        assert "chat" in result1
        assert "chien" in result1
        assert "maison" in result1
        # Stop words supprimés
        assert "le" not in result1
        assert "et" not in result1
        assert "dans" not in result1
        
        # Sans stop words
        result2 = tokenize(text1, remove_stop=False)
        assert len(result2) > len(result1)
        
        # Cas limites
        assert tokenize("", remove_stop=True) == []
        assert tokenize("   ", remove_stop=True) == []
        
        # Chiffres et lettres mélangés
        result3 = tokenize("abc123 def456 ghi789", remove_stop=False)
        assert len(result3) > 0

    def test_chunk_text_various_scenarios(self):
        """chunk_text - scénarios variés."""
        # Texte exactement chunk_size
        text1 = "a" * 1200
        result1 = chunk_text(text1, chunk_size=1200, overlap=200)
        assert len(result1) >= 1
        
        # Texte légèrement plus grand
        text2 = "b" * 1300
        result2 = chunk_text(text2, chunk_size=1200, overlap=100)
        assert len(result2) >= 2
        
        # Overlap = 0
        text3 = "mot " * 1000
        result3 = chunk_text(text3, chunk_size=500, overlap=0)
        assert len(result3) > 0
        
        # Très long texte
        text4 = "long " * 5000
        result4 = chunk_text(text4, chunk_size=1000, overlap=50)
        assert len(result4) > 10

    def test_normalize_variations(self):
        """normalize_text - variations."""
        from core.context import normalize_text
        
        # Multiples \r\n
        assert "\r" not in normalize_text("a\r\nb\r\nc\r\n")
        
        # Seulement \r
        assert "\r" not in normalize_text("x\ry\rz")
        
        # Mix
        result = normalize_text("p\r\nq\rr\ns")
        assert "\r" not in result
        assert "p" in result
        assert "s" in result
        
        # Newlines multiples
        result = normalize_text("a\n\n\n\n\n\n\nb")
        assert "\n\n\n\n" not in result

    def test_sha256_variations(self):
        """SHA256 - variations."""
        # Vide
        h1 = sha256_text("")
        assert len(h1) == 64
        
        # Court
        h2 = sha256_text("a")
        assert len(h2) == 64
        assert h2 != h1
        
        # Long
        h3 = sha256_text("x" * 10000)
        assert len(h3) == 64
        
        # Unicode
        h4 = sha256_text("café ñ ü")
        assert len(h4) == 64
        
        # Même texte = même hash
        assert sha256_text("test") == sha256_text("test")

    def test_sanitize_all_patterns(self):
        """sanitize_output - tous patterns."""
        # Backticks multiples
        assert "```" not in sanitize_output("```python\ncode\n```")
        
        # Zero-width space
        result = sanitize_output("text\u200bwith\u200bspaces")
        assert "\u200b" not in result
        
        # JSON prefix variations
        assert sanitize_output("JSON: data") == "data"
        assert sanitize_output("json:data") == "data"
        assert sanitize_output("Json: stuff") == "stuff"
        
        # Whitespace
        assert sanitize_output("  data  ") == "data"

    def test_truncate_comprehensive(self):
        """Truncation complète."""
        # Lines - beaucoup de lignes
        lines = "\n".join([f"L{i}" for i in range(1000)])
        result = truncate_lines(lines, 50)
        assert result.count("\n") <= 50
        
        # Lines - avec lignes vides
        text = "a\n\n\nb\n\n\nc"
        result = truncate_lines(text, 2)
        # Devrait ignorer les vides
        assert "a" in result
        
        # Chars - exactement à la limite
        assert len(truncate_chars("a" * 100, 100)) <= 105
        
        # Chars - bien en dessous
        assert truncate_chars("short", 1000) == "short"
        
        # Chars - très long
        long_text = "x" * 10000
        result = truncate_chars(long_text, 500)
        assert len(result) <= 510

    def test_norm_all_cases(self):
        """_norm - tous les cas."""
        assert _norm("UPPER") == "upper"
        assert _norm("MiXeD") == "mixed"
        assert _norm("  spaces  ") == "spaces"
        assert _norm("title:") == "title"
        assert _norm("Title :") == "title"
        assert _norm("a  b   c") == "a b c"
        assert _norm("test\u00a0here") == "test here"

    def test_stringify_all_types(self):
        """_stringify_answer - tous types."""
        # String
        assert _stringify_answer("text") == "text"
        
        # Int
        assert "42" in _stringify_answer(42)
        
        # Float
        assert "3.14" in _stringify_answer(3.14)
        
        # Bool
        assert _stringify_answer(True)
        assert _stringify_answer(False)
        
        # None
        assert _stringify_answer(None) == ""
        
        # List
        result = _stringify_answer(["a", "b", "c"])
        assert "a" in result
        assert "b" in result
        
        # Dict
        result = _stringify_answer({"k": "v"})
        assert isinstance(result, str)
        
        # Nested
        result = _stringify_answer({"list": [1, 2], "nested": {"x": "y"}})
        assert isinstance(result, str)

    def test_build_moustache_comprehensive(self):
        """build_moustache_mapping - complet."""
        # Simple
        data1 = {"A": "1"}
        result1 = build_moustache_mapping(data1)
        assert "{{A}}" in result1
        assert result1["{{A}}"] == "1"
        
        # Multiple
        data2 = {"A": "1", "B": "2", "C": "3"}
        result2 = build_moustache_mapping(data2)
        assert len(result2) >= 3
        assert all(k.startswith("{{") for k in result2.keys())
        
        # Types variés
        data3 = {"STR": "text", "INT": 42, "FLOAT": 3.14, "BOOL": True, "LIST": ["a"]}
        result3 = build_moustache_mapping(data3)
        assert all(isinstance(v, str) for v in result3.values())

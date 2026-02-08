"""
Database handler for storing and retrieving test results
"""
import json
import datetime
import os
from typing import List, Dict, Any

RESULTS_FILE = "results.json"

class Database:
    def __init__(self):
        self.results = self._load_results()
    
    def _load_results(self) -> List[Dict[str, Any]]:
        """Load results from JSON file"""
        if not os.path.exists(RESULTS_FILE):
            return []
        
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_results(self):
        """Save results to JSON file"""
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
    
    def save_result(self, 
                   student_id: int,
                   name: str,
                   username: str,
                   unit: int,
                   grammar_score: int,
                   vocab_score: int,
                   total_score: int,
                   percentage: float,
                   status: str) -> Dict[str, Any]:
        """Save a test result to database"""
        
        result = {
            "student_id": student_id,
            "name": name,
            "username": username,
            "unit": unit,
            "grammar_score": grammar_score,
            "vocab_score": vocab_score,
            "total_score": total_score,
            "percentage": percentage,
            "status": status,
            "date_time": datetime.datetime.now().isoformat()
        }
        
        self.results.append(result)
        self._save_results()
        
        return result
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all test results"""
        return self.results
    
    def get_student_results(self, student_id: int) -> List[Dict[str, Any]]:
        """Get all results for a specific student"""
        return [r for r in self.results if r["student_id"] == student_id]
    
    def get_unit_results(self, unit: int) -> List[Dict[str, Any]]:
        """Get all results for a specific unit"""
        return [r for r in self.results if r["unit"] == unit]
    
    def export_results(self, filename: str = None) -> str:
        """Export results to JSON file"""
        if not filename:
            filename = f"results_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self.results:
            return {}
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        # Average scores
        avg_grammar = sum(r["grammar_score"] for r in self.results) / total_tests
        avg_vocab = sum(r["vocab_score"] for r in self.results) / total_tests
        avg_total = sum(r["total_score"] for r in self.results) / total_tests
        avg_percentage = sum(r["percentage"] for r in self.results) / total_tests
        
        # Tests per unit
        unit_counts = {}
        for unit in range(1, 9):
            unit_counts[f"unit_{unit}"] = sum(1 for r in self.results if r["unit"] == unit)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "avg_grammar_score": round(avg_grammar, 2),
            "avg_vocab_score": round(avg_vocab, 2),
            "avg_total_score": round(avg_total, 2),
            "avg_percentage": round(avg_percentage, 2),
            "tests_per_unit": unit_counts,
            "last_test_date": max(r["date_time"] for r in self.results) if self.results else None
        }

# Global database instance
db = Database()
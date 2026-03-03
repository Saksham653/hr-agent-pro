import os
import pytest


class TestQueryDifferentiation:
    def setup_method(self):
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY", "")

    def test_position_synonym_job(self):
        from app.backend import get_response
        res = get_response(user_input="whats your job", user="Alexander Verdad", session_id="Alexander Verdad")
        assert res["model_used"] == "local"
        assert "position" in res["response"].lower()

    def test_supervisor_synonyms(self):
        from app.backend import get_response
        res = get_response(user_input="who is my boss?", user="Alexander Verdad", session_id="Alexander Verdad")
        assert res["model_used"] == "local"
        assert "supervisor" in res["response"].lower()

    def test_department_synonyms(self):
        from app.backend import get_response
        res = get_response(user_input="which team am i in?", user="Alexander Verdad", session_id="Alexander Verdad")
        assert res["model_used"] == "local"
        assert "works in the" in res["response"].lower()

    def test_salary_query(self):
        from app.backend import get_response
        res = get_response(user_input="what is my salary?", user="Alexander Verdad", session_id="Alexander Verdad")
        assert res["model_used"] == "local"
        assert "basic pay" in res["response"].lower()

    def test_distinct_responses(self):
        from app.backend import get_response
        a = get_response(user_input="hello", user="Alexander Verdad", session_id="Alexander Verdad")
        b = get_response(user_input="which team am i in?", user="Alexander Verdad", session_id="Alexander Verdad")
        c = get_response(user_input="what is my salary?", user="Alexander Verdad", session_id="Alexander Verdad")
        assert a["response"] != b["response"] != c["response"]


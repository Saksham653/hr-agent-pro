import os
import pytest


class TestMessagingSystem:
    def setup_method(self):
        # Ensure env keys are absent to exercise local path
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        os.environ["PINECONE_API_KEY"] = os.getenv("PINECONE_API_KEY", "")

    def test_greeting_uses_local_model(self):
        from app.backend import get_response
        result = get_response(user_input="hey", user="Alexander Verdad", session_id="Alexander Verdad")
        assert result["model_used"] == "local"
        assert "Ask me about your leave" in result["response"]
        assert result["error"] is None

    def test_vacation_balance_is_personalized(self):
        from app.backend import get_response
        result = get_response(
            user_input="how many vacation leave do i left with",
            user="Alexander Verdad",
            session_id="Alexander Verdad"
        )
        assert result["model_used"] == "local"
        assert "Alexander Verdad has" in result["response"]
        assert "vacation" in result["response"].lower()

    def test_department_query_varies_response(self):
        from app.backend import get_response
        res1 = get_response(user_input="hello", user="Alexander Verdad", session_id="Alexander Verdad")
        res2 = get_response(user_input="which department am i in?", user="Alexander Verdad", session_id="Alexander Verdad")
        assert res1["model_used"] == "local"
        assert res2["model_used"] == "local"
        assert res1["response"] != res2["response"]


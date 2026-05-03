"""Tests for /contexts/{id}/messages endpoints."""


class TestMessages:
    def test_empty_on_new_context(self, client, fresh_context):
        r = client.get(f"/contexts/{fresh_context}/messages")
        assert r.status_code == 200
        assert r.json() == []

    def test_save_and_retrieve_user_message(self, client, fresh_context):
        client.post(f"/contexts/{fresh_context}/messages",
                    json={"role": "user", "content": "Hello agent"})
        msgs = client.get(f"/contexts/{fresh_context}/messages").json()
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello agent"
        assert "timestamp" in msgs[0]

    def test_save_assistant_message_with_sources(self, client, fresh_context):
        client.post(f"/contexts/{fresh_context}/messages", json={
            "role": "assistant",
            "content": "The answer is 42.",
            "sources": [{"source": "doc.pdf", "score": 0.9, "text": "ctx", "source_type": "pdf"}],
            "action_taken": "SEARCH",
            "iterations": 1,
        })
        msgs = client.get(f"/contexts/{fresh_context}/messages").json()
        assert msgs[0]["role"] == "assistant"
        assert msgs[0]["action_taken"] == "SEARCH"
        assert len(msgs[0]["sources"]) == 1

    def test_messages_returned_in_chronological_order(self, client, fresh_context):
        for content in ("alpha", "beta", "gamma"):
            client.post(f"/contexts/{fresh_context}/messages",
                        json={"role": "user", "content": content})
        msgs = client.get(f"/contexts/{fresh_context}/messages").json()
        assert len(msgs) == 3
        assert msgs[0]["content"] == "alpha"
        assert msgs[-1]["content"] == "gamma"

    def test_messages_are_context_scoped(self, client, fresh_context):
        other = client.post("/contexts", json={"name": "Other"}).json()["context_id"]
        client.post(f"/contexts/{fresh_context}/messages",
                    json={"role": "user", "content": "mine"})
        assert client.get(f"/contexts/{other}/messages").json() == []
        client.delete(f"/contexts/{other}")

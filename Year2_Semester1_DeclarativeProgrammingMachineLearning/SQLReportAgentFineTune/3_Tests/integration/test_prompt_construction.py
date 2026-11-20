"""Integration tests for ChatML prompt construction."""

from app.inference.prompt_template import PromptBuilder


def test_prompt_builder():
    builder = PromptBuilder()
    schema_txt = "- Table `users`: id, name"
    question = "List all user names."
    msgs = builder.build_messages(schema_txt, question)

    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert "- Table `users`: id, name" in msgs[1]["content"]
    assert "List all user names." in msgs[1]["content"]

    rendered = builder.build_prompt_with_tokenizer(None, schema_txt, question)
    assert "<|im_start|>system" in rendered
    assert "<|im_start|>user" in rendered
    assert "<|im_start|>assistant\n" in rendered

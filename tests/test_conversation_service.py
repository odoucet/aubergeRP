"""Tests for ConversationService — direct service calls, no HTTP."""
from __future__ import annotations

from pathlib import Path

import pytest

from aubergeRP.models.character import CharacterData
from aubergeRP.services.character_service import CharacterNotFoundError, CharacterService
from aubergeRP.services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
    resolve_macros,
)


def make_services(tmp_path: Path):
    char_svc = CharacterService(data_dir=tmp_path)
    conv_svc = ConversationService(data_dir=tmp_path, character_service=char_svc)
    return char_svc, conv_svc


def make_character(char_svc: CharacterService, **overrides):
    base = dict(
        name="Elara",
        description="An elven ranger.",
        first_mes="Hello, {{user}}! I am {{char}}.",
    )
    base.update(overrides)
    return char_svc.create_character(CharacterData(**base))


# ---------------------------------------------------------------------------
# resolve_macros
# ---------------------------------------------------------------------------

def test_resolve_char():
    assert resolve_macros("Hello {{char}}", "Elara") == "Hello Elara"


def test_resolve_user():
    assert resolve_macros("Hi {{user}}", "Elara", "Bob") == "Hi Bob"


def test_resolve_unknown_passthrough():
    assert resolve_macros("{{unknown}}", "X") == "{{unknown}}"


def test_resolve_multiple():
    result = resolve_macros("I am {{char}}, you are {{user}}", "Elara", "Bob")
    assert result == "I am Elara, you are Bob"


def test_resolve_default_user():
    assert resolve_macros("{{user}}", "X") == "User"


# ---------------------------------------------------------------------------
# create_conversation
# ---------------------------------------------------------------------------

def test_create_returns_conversation(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    assert conv.id
    assert conv.character_id == char.id
    assert conv.character_name == "Elara"


def test_create_inserts_first_mes(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    assert len(conv.messages) == 1
    assert conv.messages[0].role == "assistant"


def test_create_first_mes_resolves_macros(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id, user_name="Bob")
    assert "Bob" in conv.messages[0].content
    assert "Elara" in conv.messages[0].content


def test_create_no_first_mes_empty_messages(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv = conv_svc.create_conversation(char.id)
    assert conv.messages == []


def test_create_character_not_found(tmp_path):
    _, conv_svc = make_services(tmp_path)
    with pytest.raises(CharacterNotFoundError):
        conv_svc.create_conversation("nonexistent")


def test_create_title_is_character_name(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    assert conv.title.startswith("Elara — ")


# ---------------------------------------------------------------------------
# persistence / get
# ---------------------------------------------------------------------------

def test_get_conversation(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    loaded = conv_svc.get_conversation(conv.id)
    assert loaded.id == conv.id
    assert loaded.character_name == "Elara"


def test_persistence_to_disk(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    assert (tmp_path / "conversations" / f"{conv.id}.json").exists()


def test_get_not_found(tmp_path):
    _, conv_svc = make_services(tmp_path)
    with pytest.raises(ConversationNotFoundError):
        conv_svc.get_conversation("nonexistent")


def test_get_preserves_messages(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    loaded = conv_svc.get_conversation(conv.id)
    assert len(loaded.messages) == len(conv.messages)


# ---------------------------------------------------------------------------
# list_conversations
# ---------------------------------------------------------------------------

def test_list_empty(tmp_path):
    _, conv_svc = make_services(tmp_path)
    assert conv_svc.list_conversations() == []


def test_list_returns_summaries(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv_svc.create_conversation(char.id)
    conv_svc.create_conversation(char.id)
    result = conv_svc.list_conversations()
    assert len(result) == 2


def test_list_filter_by_character(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char1 = make_character(char_svc, name="Elara")
    char2 = make_character(char_svc, name="Darian", description="A minstrel.")
    conv_svc.create_conversation(char1.id)
    conv_svc.create_conversation(char2.id)
    result = conv_svc.list_conversations(character_id=char1.id)
    assert len(result) == 1
    assert result[0].character_name == "Elara"


def test_list_filter_no_match(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv_svc.create_conversation(char.id)
    result = conv_svc.list_conversations(character_id="other-id")
    assert result == []


def test_list_summary_message_count(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv_svc.create_conversation(char.id)
    summaries = conv_svc.list_conversations()
    assert summaries[0].message_count == 1


def test_list_summary_no_messages(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv_svc.create_conversation(char.id)
    summaries = conv_svc.list_conversations()
    assert summaries[0].message_count == 0


# ---------------------------------------------------------------------------
# delete_conversation
# ---------------------------------------------------------------------------

def test_delete_removes_conversation(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    conv = conv_svc.create_conversation(char.id)
    conv_svc.delete_conversation(conv.id)
    with pytest.raises(ConversationNotFoundError):
        conv_svc.get_conversation(conv.id)
    assert not (tmp_path / "conversations" / f"{conv.id}.json").exists()


def test_delete_not_found(tmp_path):
    _, conv_svc = make_services(tmp_path)
    with pytest.raises(ConversationNotFoundError):
        conv_svc.delete_conversation("nonexistent")


def test_delete_reduces_list(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc)
    c1 = conv_svc.create_conversation(char.id)
    conv_svc.create_conversation(char.id)
    conv_svc.delete_conversation(c1.id)
    assert len(conv_svc.list_conversations()) == 1


# ---------------------------------------------------------------------------
# append_message
# ---------------------------------------------------------------------------

def test_append_message_returns_message(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv = conv_svc.create_conversation(char.id)
    msg = conv_svc.append_message(conv.id, "user", "Hello!")
    assert msg.role == "user"
    assert msg.content == "Hello!"
    assert msg.id


def test_append_message_persists(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv = conv_svc.create_conversation(char.id)
    conv_svc.append_message(conv.id, "user", "Hello!")
    reloaded = conv_svc.get_conversation(conv.id)
    assert len(reloaded.messages) == 1
    assert reloaded.messages[0].content == "Hello!"


def test_append_message_increments(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv = conv_svc.create_conversation(char.id)
    conv_svc.append_message(conv.id, "user", "Hi")
    conv_svc.append_message(conv.id, "assistant", "Hello back")
    reloaded = conv_svc.get_conversation(conv.id)
    assert len(reloaded.messages) == 2
    assert reloaded.messages[1].content == "Hello back"


def test_append_message_not_found(tmp_path):
    _, conv_svc = make_services(tmp_path)
    with pytest.raises(ConversationNotFoundError):
        conv_svc.append_message("nonexistent", "user", "Hi")


def test_append_message_with_images(tmp_path):
    char_svc, conv_svc = make_services(tmp_path)
    char = make_character(char_svc, first_mes="")
    conv = conv_svc.create_conversation(char.id)
    msg = conv_svc.append_message(conv.id, "assistant", "Look!", images=["img1.png"])
    assert msg.images == ["img1.png"]

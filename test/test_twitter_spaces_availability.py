import pytest

def is_twitter_space_available(metadata):
    """
    Verifica se um Twitter Space está disponível para download.
    Um espaço só é considerado disponível se:
    - Não está ao vivo
    - Não está agendado (upcoming)
    - Não é privado
    """
    return (
        metadata.get("is_live") is False
        and metadata.get("live_status") not in ["is_upcoming", "upcoming"]
        and metadata.get("availability") != "private"
    )

def test_space_is_available_when_not_live_not_upcoming_and_not_private():
    metadata = {
        'is_live': False,
        'live_status': None,
        'availability': 'public'
    }
    assert is_twitter_space_available(metadata) is True, "Twitter Space deveria ser considerado disponível"

def test_space_is_not_available_when_upcoming():
    metadata = {
        'is_live': False,
        'live_status': "is_upcoming",
        'availability': 'public'
    }
    assert is_twitter_space_available(metadata) is False, "Twitter Space agendado não deveria ser considerado disponível"
    
def test_space_is_not_available_when_private():
    metadata = {
        'is_live': False,
        'live_status': None,
        'availability': 'private'
    }
    assert is_twitter_space_available(metadata) is False, "Twitter Space privado não deveria ser considerado disponível"

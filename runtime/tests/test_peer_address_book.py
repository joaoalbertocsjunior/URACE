"""Unit tests for peer_address_book (F7-lite)."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))
from urace.peer_address_book import PeerAddressBook, MAX_PEERS, MAX_URLS_PER_PEER


def _book(tmp_path):
    return PeerAddressBook(tmp_path / 'peer_address_book.json')


def test_record_and_retrieve(tmp_path):
    """record() stores endpoint; endpoints_for() returns it best-first."""
    book = _book(tmp_path)
    book.record('peer-aaa', 'https://a.example.com:7301')
    book.record('peer-aaa', 'https://b.example.com:7301')
    # Second record should be first (MRU)
    eps = book.endpoints_for('peer-aaa')
    assert eps[0] == 'https://b.example.com:7301'
    assert 'https://a.example.com:7301' in eps
    assert len(eps) == 2

    # Unknown peer returns empty list
    assert book.endpoints_for('peer-unknown') == []

    # Persist and reload
    book.save()
    book2 = PeerAddressBook(tmp_path / 'peer_address_book.json')
    assert 'https://b.example.com:7301' in book2.endpoints_for('peer-aaa')


def test_merge_from_remote(tmp_path):
    """merge() adds remote entries; never evicts local entries."""
    book = _book(tmp_path)
    book.record('peer-local', 'https://local.example.com:7301')

    remote = {
        'peer-local': ['https://local.example.com:7301', 'https://extra.example.com:7301'],
        'peer-remote': ['https://remote.example.com:7301'],
    }
    book.merge(remote)

    # local peer gets extra url appended
    local_eps = book.endpoints_for('peer-local')
    assert 'https://local.example.com:7301' in local_eps
    assert 'https://extra.example.com:7301' in local_eps

    # new remote peer added
    assert 'https://remote.example.com:7301' in book.endpoints_for('peer-remote')

    # all_entries returns both
    entries = book.all_entries()
    assert 'peer-local' in entries
    assert 'peer-remote' in entries

    # merge ignores bad input gracefully
    book.merge(None)
    book.merge({'bad': 'not-a-list'})
    book.merge({'': ['https://x.example.com']})


def test_lru_eviction_at_max_size(tmp_path):
    """When MAX_PEERS is reached, LRU (oldest) peer is evicted on new record."""
    book = _book(tmp_path)

    # Fill to capacity
    for i in range(MAX_PEERS):
        book.record(f'peer-{i:04d}', f'https://peer{i}.example.com:7301')

    assert len(book.all_entries()) == MAX_PEERS

    # The first peer recorded (peer-0000) should be LRU
    # Adding a new peer must evict LRU
    book.record('peer-new', 'https://new.example.com:7301')

    entries = book.all_entries()
    assert len(entries) == MAX_PEERS
    assert 'peer-new' in entries
    # peer-0000 was LRU and should be evicted
    assert 'peer-0000' not in entries
    # peer-0001 through peer-(MAX_PEERS-1) should still be present
    assert f'peer-{MAX_PEERS-1:04d}' in entries

    # URLs per peer capped at MAX_URLS_PER_PEER
    for j in range(MAX_URLS_PER_PEER + 3):
        book.record('peer-multi', f'https://multi{j}.example.com:7301')
    assert len(book.endpoints_for('peer-multi')) <= MAX_URLS_PER_PEER

import pytest
from unittest.mock import Mock, patch
from utils.telegram import TelegramAlert


def test_telegram_send_calls_api_correctly():
    """send() makes POST to correct Telegram API endpoint"""
    with patch('utils.telegram.requests.post') as mock_post:
        mock_post.return_value.status_code = 200

        telegram = TelegramAlert('fake-token', '123456')
        result = telegram.send('Test message')

        assert result is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'https://api.telegram.org/bot' in args[0]
        assert kwargs['json']['text'] == 'Test message'
        assert kwargs['json']['chat_id'] == '123456'


def test_telegram_send_returns_false_on_error():
    """send() returns False and logs error on HTTP failure"""
    with patch('utils.telegram.requests.post') as mock_post:
        mock_post.side_effect = Exception('Network error')

        telegram = TelegramAlert('fake-token', '123456')
        result = telegram.send('Test')

        assert result is False


def test_format_whois_alert_new_domain():
    """format_whois_alert() formats new domain alert correctly"""
    telegram = TelegramAlert('token', 'chat')

    change = {
        'type': 'new_domain',
        'domain': 'flamengoshop2027.com.br',
        'registrar': 'Registro.br'
    }

    msg = telegram.format_whois_alert('Flamengo', change)

    assert '🔍' in msg
    assert 'SINAL: Novo Domínio' in msg
    assert 'Flamengo' in msg
    assert 'flamengoshop2027.com.br' in msg
    assert 'Registro.br' in msg
    assert 'Tipo: Investigativo' in msg


def test_format_site_alert():
    """format_site_alert() formats site change alert correctly"""
    telegram = TelegramAlert('token', 'chat')

    change = {'type': 'content_changed'}

    msg = telegram.format_site_alert(
        'Real Madrid',
        'First Team Squad',
        'https://www.realmadrid.com/en/football/squad',
        change
    )

    assert '🔍' in msg
    assert 'SINAL: Mudança em Site Oficial' in msg
    assert 'Real Madrid' in msg
    assert 'First Team Squad' in msg
    assert 'https://www.realmadrid.com/en/football/squad' in msg
    assert 'Tipo: Investigativo' in msg


def test_format_trends_alert_spike():
    """format_trends_alert() formats spike alert with percentage"""
    telegram = TelegramAlert('token', 'chat')

    data = {
        'interest_score': 96,
        'avg_7d': 48,
        'spike': True
    }

    msg = telegram.format_trends_alert('Manchester City', 'Haaland', data)

    assert '📈' in msg
    assert 'SINAL: Pico de Busca' in msg
    assert 'Manchester City' in msg
    assert 'Haaland' in msg
    assert '96/100' in msg
    assert '100%' in msg  # (96/48 - 1) * 100 = 100% exato
    assert 'Tipo: Demanda' in msg

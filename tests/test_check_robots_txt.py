import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.robotparser import RobotFileParser
import yaml

# Import the module (will be created next)
from scripts.check_robots_txt import check_robots_txt, check_from_yaml


class TestCheckRobotsTxt:
    """Test robots.txt validation function"""

    def test_check_robots_txt_404_returns_allowed_true(self):
        """404 response means no robots.txt, which allows by default"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = check_robots_txt('https://www.example.com')

            assert result['allowed'] is True
            assert result['status'] == 'no_robots_txt'
            assert result['robots_url'] == 'https://www.example.com/robots.txt'

    def test_check_robots_txt_200_with_allow_returns_allowed_true(self):
        """200 response with no disallow rules allows access"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            with patch('scripts.check_robots_txt.RobotFileParser') as mock_parser_class:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = 'User-agent: *\nAllow: /'
                mock_get.return_value = mock_response

                mock_parser = MagicMock()
                mock_parser.can_fetch.return_value = True
                mock_parser_class.return_value = mock_parser

                result = check_robots_txt('https://www.example.com')

                assert result['allowed'] is True
                assert result['status'] == 'parsed'
                mock_parser.set_url.assert_called_with('https://www.example.com/robots.txt')
                mock_parser.can_fetch.assert_called_with('ZooomBot', 'https://www.example.com')

    def test_check_robots_txt_200_with_disallow_returns_allowed_false(self):
        """200 response with disallow rules blocks access"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            with patch('scripts.check_robots_txt.RobotFileParser') as mock_parser_class:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = 'User-agent: *\nDisallow: /'
                mock_get.return_value = mock_response

                mock_parser = MagicMock()
                mock_parser.can_fetch.return_value = False
                mock_parser_class.return_value = mock_parser

                result = check_robots_txt('https://www.example.com')

                assert result['allowed'] is False
                assert result['status'] == 'parsed'
                assert 'Blocked by robots.txt' in result['note']

    def test_check_robots_txt_500_returns_allowed_false(self):
        """5xx response requires manual review"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = check_robots_txt('https://www.example.com')

            assert result['allowed'] is False
            assert result['status'] == 'error'
            assert 'HTTP 500' in result['note']

    def test_check_robots_txt_timeout_returns_allowed_false(self):
        """Timeout requires manual review"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.Timeout()

            result = check_robots_txt('https://www.example.com')

            assert result['allowed'] is False
            assert result['status'] == 'timeout'
            assert 'Timeout' in result['note']

    def test_check_robots_txt_network_error_returns_allowed_false(self):
        """Network error requires manual review"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            import requests
            mock_get.side_effect = requests.exceptions.ConnectionError('Connection failed')

            result = check_robots_txt('https://www.example.com')

            assert result['allowed'] is False
            assert result['status'] == 'network_error'
            assert 'ConnectionError' in result['note']

    def test_check_robots_txt_parse_error_returns_allowed_false(self):
        """Parse error requires manual review"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            with patch('scripts.check_robots_txt.RobotFileParser') as mock_parser_class:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.text = 'invalid robots.txt'
                mock_get.return_value = mock_response

                mock_parser_class.side_effect = Exception('Parse error')

                result = check_robots_txt('https://www.example.com')

                assert result['allowed'] is False
                assert result['status'] == 'parse_error'

    def test_check_robots_txt_returns_robots_url(self):
        """Result includes robots_url"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = check_robots_txt('https://www.flamengo.com.br')

            assert result['robots_url'] == 'https://www.flamengo.com.br/robots.txt'

    def test_check_from_yaml_loads_clubs_and_checks_each(self, tmp_path):
        """check_from_yaml loads YAML and validates each club's official_site URL"""
        yaml_content = """
clubs:
  - id: club1
    name: "Club One"
    official_site:
      url: "https://club1.com"
  - id: club2
    name: "Club Two"
    official_site:
      url: "https://club2.com"
"""
        yaml_file = tmp_path / "clubs.yaml"
        yaml_file.write_text(yaml_content)

        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with patch('builtins.print'):
                check_from_yaml(yaml_file)

            # Verify both URLs were checked
            assert mock_get.call_count == 2
            calls = [call[0][0] for call in mock_get.call_args_list]
            assert 'https://club1.com/robots.txt' in calls
            assert 'https://club2.com/robots.txt' in calls

    def test_check_robots_txt_includes_http_status_code_in_error_response(self):
        """Error responses include HTTP status code"""
        with patch('scripts.check_robots_txt.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_get.return_value = mock_response

            result = check_robots_txt('https://www.example.com')

            assert result['http_code'] == 403
            assert 'HTTP 403' in result['note']

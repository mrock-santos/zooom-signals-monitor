import requests
import logging


class TelegramAlert:
    """Telegram alert sender with formatted message methods."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram alert sender.

        Args:
            bot_token: Telegram bot token
            chat_id: Target chat/channel ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.logger = logging.getLogger('monitor')

    def send(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """
        Send formatted message to Telegram.

        Args:
            message: Message text (Markdown formatted)
            parse_mode: 'Markdown' or 'HTML'

        Returns:
            True if sent successfully, False otherwise
        """
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=10)
            resp.raise_for_status()
            self.logger.info("Telegram alert sent successfully")
            return True

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Telegram HTTP error: {e.response.status_code} - {e.response.text}")
            return False

        except requests.exceptions.Timeout:
            self.logger.error("Telegram send timeout (10s)")
            return False

        except Exception as e:
            self.logger.error(f"Telegram send failed: {type(e).__name__}: {e}")
            return False

    def format_whois_alert(self, club_name: str, change: dict) -> str:
        """
        Format WHOIS change alert.

        Args:
            club_name: Name of the club
            change: Dict with keys: type, domain, (registrar|old|new|...)

        Returns:
            Formatted Markdown message
        """
        emoji = "🔍"
        change_type = change['type']

        if change_type == 'new_domain':
            msg = f"{emoji} *SINAL: Novo Domínio*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Fonte:* WHOIS\n"
            msg += f"*Domínio:* `{change['domain']}`\n"
            msg += f"*Registrar:* {change.get('registrar', 'N/A')}\n\n"
            msg += f"_Tipo: Investigativo_"

        elif change_type == 'registrar_changed':
            msg = f"{emoji} *SINAL: Mudança de Registrar*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Domínio:* `{change['domain']}`\n"
            msg += f"*Mudou de:* {change['old']}\n"
            msg += f"*Para:* {change['new']}\n\n"
            msg += f"_Tipo: Investigativo_"

        elif change_type == 'nameservers_changed':
            msg = f"{emoji} *SINAL: Nameservers Alterados*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Domínio:* `{change['domain']}`\n"
            if change.get('added'):
                msg += f"*Adicionados:* {', '.join(change['added'])}\n"
            if change.get('removed'):
                msg += f"*Removidos:* {', '.join(change['removed'])}\n"
            msg += f"\n_Tipo: Investigativo_"

        elif change_type == 'whois_updated':
            msg = f"{emoji} *SINAL: WHOIS Atualizado*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Domínio:* `{change['domain']}`\n"
            msg += f"*Nova data de atualização:* {change['new_update_date']}\n\n"
            msg += f"_Tipo: Investigativo_"

        elif change_type == 'expiring_soon':
            msg = f"{emoji} *SINAL: Domínio Expirando*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Domínio:* `{change['domain']}`\n"
            msg += f"*Expira em:* {change['expiry_date']} ({change['days_left']} dias)\n\n"
            msg += f"_Tipo: Investigativo_"

        else:
            # Fallback genérico
            msg = f"{emoji} *SINAL: WHOIS*\n\n"
            msg += f"*Clube:* {club_name}\n"
            msg += f"*Tipo:* {change_type}\n\n"
            msg += f"_Tipo: Investigativo_"

        return msg

    def format_site_alert(self, club_name: str, page_label: str, page_url: str, change: dict) -> str:
        """
        Format site monitoring alert.

        Args:
            club_name: Name of the club
            page_label: Human-readable page name (e.g., "First Team Squad")
            page_url: Full URL of the monitored page
            change: Dict with change details

        Returns:
            Formatted Markdown message
        """
        msg = f"🔍 *SINAL: Mudança em Site Oficial*\n\n"
        msg += f"*Clube:* {club_name}\n"
        msg += f"*Fonte:* Site Monitoring\n"
        msg += f"*Página:* {page_label}\n"
        msg += f"*Evento:* Conteúdo alterado\n\n"
        msg += f"🔗 Verificar: {page_url}\n\n"
        msg += f"_Tipo: Investigativo_"
        return msg

    def format_trends_alert(self, club_name: str, keyword: str, data: dict) -> str:
        """
        Format Google Trends spike alert.

        Args:
            club_name: Name of the club
            keyword: Search keyword
            data: Dict with keys: interest_score, avg_7d, spike

        Returns:
            Formatted Markdown message
        """
        msg = f"📈 *SINAL: Pico de Busca*\n\n"
        msg += f"*Clube:* {club_name}\n"
        msg += f"*Fonte:* Google Trends\n"
        msg += f"*Termo:* {keyword}\n"
        msg += f"*Interesse:* {data['interest_score']}/100"

        if data.get('spike'):
            pct_increase = ((data['interest_score'] / data['avg_7d']) - 1) * 100
            msg += f" (↑ {pct_increase:.0f}% vs. média 7d)\n"
        else:
            msg += "\n"

        msg += f"*Região:* Brasil\n\n"
        msg += f"_Tipo: Demanda_"
        return msg

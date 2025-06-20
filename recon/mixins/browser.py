import mechanize
import socket
import ssl
import logging
from urllib.parse import urlparse
from typing import Dict, Optional, Any


class BrowserMixin:
    """
    Mixin-Klasse für mechanize.Browser mit erweiterten Konfigurationsoptionen.

    Bietet eine standardisierte Methode zur Browser-Konfiguration mit:
    - User-Agent-Management
    - Proxy-Unterstützung
    - Debug-Optionen
    - Timeout-Konfiguration
    - SSL-Verifikation
    - Cookie-Handling
    """

    def __init__(self):
        # Standardoptionen falls _global_options nicht definiert ist
        if not hasattr(self, '_global_options'):
            self._global_options = self._get_default_options()

        # Logger für Debug-Zwecke
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_default_options(self) -> Dict[str, Any]:
        """Gibt Standard-Konfigurationsoptionen zurück."""
        return {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'verbosity': 0,
            'proxy': None,
            'timeout': 30,
            'verify_ssl': True,
            'follow_redirects': True,
            'max_redirects': 10,
            'handle_cookies': True,
            'handle_refresh': True,
            'ignore_robots': True
        }

    def get_browser(self) -> mechanize.Browser:
        """
        Erstellt und konfiguriert eine mechanize.Browser-Instanz.

        Returns:
            mechanize.Browser: Konfigurierte Browser-Instanz

        Raises:
            ValueError: Bei ungültigen Proxy-Einstellungen
            ConnectionError: Bei Netzwerkproblemen
        """
        try:
            br = mechanize.Browser()

            # User-Agent konfigurieren
            self._configure_user_agent(br)

            # Debug-Optionen setzen
            self._configure_debug_options(br)

            # Proxy konfigurieren
            self._configure_proxy(br)

            # Browser-Verhalten konfigurieren
            self._configure_browser_behavior(br)

            # Timeout global setzen
            self._configure_timeout()

            # SSL-Konfiguration
            self._configure_ssl()

            self.logger.debug("Browser erfolgreich konfiguriert")
            return br

        except Exception as e:
            self.logger.error(f"Fehler beim Erstellen des Browsers: {e}")
            raise

    def _configure_user_agent(self, browser: mechanize.Browser) -> None:
        """Konfiguriert den User-Agent Header."""
        user_agent = self._global_options.get('user-agent')
        if user_agent:
            browser.addheaders = [('User-agent', user_agent)]
            self.logger.debug(f"User-Agent gesetzt: {user_agent}")

    def _configure_debug_options(self, browser: mechanize.Browser) -> None:
        """Konfiguriert Debug-Optionen basierend auf Verbosity-Level."""
        verbosity = self._global_options.get('verbosity', 0)

        if verbosity >= 2:
            browser.set_debug_http(True)
            browser.set_debug_redirects(True)
            browser.set_debug_responses(True)
            self.logger.debug("Debug-Modus aktiviert")

        if verbosity >= 3:
            # Zusätzliche Debug-Optionen
            logging.basicConfig(level=logging.DEBUG)

    def _configure_proxy(self, browser: mechanize.Browser) -> None:
        """Konfiguriert Proxy-Einstellungen."""
        proxy = self._global_options.get('proxy')

        if proxy:
            # Validiere Proxy-Format
            if not self._validate_proxy(proxy):
                raise ValueError(f"Ungültiges Proxy-Format: {proxy}")

            proxy_dict = {
                'http': proxy,
                'https': proxy
            }
            browser.set_proxies(proxy_dict)
            self.logger.debug(f"Proxy konfiguriert: {proxy}")

    def _configure_browser_behavior(self, browser: mechanize.Browser) -> None:
        """Konfiguriert allgemeines Browser-Verhalten."""
        # Robots.txt ignorieren
        ignore_robots = self._global_options.get('ignore_robots', True)
        browser.set_handle_robots(not ignore_robots)

        # Redirects behandeln
        follow_redirects = self._global_options.get('follow_redirects', True)
        browser.set_handle_redirect(follow_redirects)

        # Cookies behandeln
        handle_cookies = self._global_options.get('handle_cookies', True)
        browser.set_handle_equiv(handle_cookies)

        # Refresh-Header behandeln
        handle_refresh = self._global_options.get('handle_refresh', True)
        browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),
                                   max_time=1, honor_time=handle_refresh)

        # Maximale Anzahl von Redirects
        max_redirects = self._global_options.get('max_redirects', 10)
        if hasattr(browser, 'set_handle_redirect'):
            # Implementierung abhängig von mechanize-Version
            pass

    def _configure_timeout(self) -> None:
        """Konfiguriert Socket-Timeout global."""
        timeout = self._global_options.get('timeout', 30)
        socket.setdefaulttimeout(timeout)
        self.logger.debug(f"Socket-Timeout gesetzt: {timeout}s")

    def _configure_ssl(self) -> None:
        """Konfiguriert SSL-Verifikation."""
        verify_ssl = self._global_options.get('verify_ssl', True)

        if not verify_ssl:
            # SSL-Verifikation deaktivieren (Vorsicht!)
            ssl._create_default_https_context = ssl._create_unverified_context
            self.logger.warning("SSL-Verifikation deaktiviert!")

    def _validate_proxy(self, proxy: str) -> bool:
        """
        Validiert Proxy-Format.

        Args:
            proxy: Proxy-String (z.B. "http://proxy.example.com:8080")

        Returns:
            bool: True wenn gültig, False sonst
        """
        try:
            parsed = urlparse(proxy)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False

    def create_session_browser(self, session_config: Optional[Dict] = None) -> mechanize.Browser:
        """
        Erstellt einen Browser mit Session-spezifischen Einstellungen.

        Args:
            session_config: Zusätzliche Konfiguration für diese Session

        Returns:
            mechanize.Browser: Konfigurierte Browser-Instanz
        """
        # Temporär Optionen überschreiben
        original_options = self._global_options.copy()

        if session_config:
            self._global_options.update(session_config)

        try:
            browser = self.get_browser()
            return browser
        finally:
            # Ursprüngliche Optionen wiederherstellen
            self._global_options = original_options

    def test_browser_connection(self, test_url: str = "http://httpbin.org/get") -> bool:
        """
        Testet die Browser-Konfiguration mit einer Test-URL.

        Args:
            test_url: URL zum Testen der Verbindung

        Returns:
            bool: True bei erfolgreichem Test, False sonst
        """
        try:
            browser = self.get_browser()
            response = browser.open(test_url)

            if response.code == 200:
                self.logger.info("Browser-Test erfolgreich")
                return True
            else:
                self.logger.warning(f"Browser-Test fehlgeschlagen: HTTP {response.code}")
                return False

        except Exception as e:
            self.logger.error(f"Browser-Test fehlgeschlagen: {e}")
            return False


# Beispiel für eine Framework-Klasse die das Mixin verwendet
class WebScrapingFramework(BrowserMixin):
    """Beispiel-Framework das das BrowserMixin verwendet."""

    def __init__(self, **options):
        # Globale Optionen setzen
        self._global_options = {
            'user-agent': 'Custom-Scraper/1.0',
            'verbosity': 1,
            'proxy': None,
            'timeout': 60,
            'verify_ssl': True,
            'follow_redirects': True,
            'handle_cookies': True
        }

        # Optionen überschreiben falls angegeben
        self._global_options.update(options)

        super().__init__()

    def scrape_url(self, url: str) -> str:
        """Beispiel-Methode zum Scrapen einer URL."""
        browser = self.get_browser()

        try:
            response = browser.open(url)
            return response.read().decode('utf-8')
        except Exception as e:
            self.logger.error(f"Fehler beim Scrapen von {url}: {e}")
            raise


# Verwendungsbeispiel
if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(level=logging.INFO)

    # Framework mit benutzerdefinierten Optionen erstellen
    scraper = WebScrapingFramework(
        verbosity=2,
        timeout=30,
        proxy="http://proxy.example.com:8080"  # Falls benötigt
    )

    # Browser-Verbindung testen
    if scraper.test_browser_connection():
        print("Browser-Konfiguration erfolgreich!")

        # Session-spezifischen Browser erstellen
        session_browser = scraper.create_session_browser({
            'user-agent': 'Session-Specific-Agent/1.0',
            'timeout': 45
        })

        print("Session-Browser erstellt")
    else:
        print("Browser-Konfiguration fehlgeschlagen!")

"""modules/scanner.py — Background scheduler for SSL scans and email alerts."""
import threading
import time
import logging

import schedule
from modules.db import SiteRepo, ResultRepo

logger = logging.getLogger(__name__)


def scan_sites(app):
    """Re-check every site's SSL certificate and update results table."""
    with app.app_context():
        from modules.cert_checker import get_cert_details
        logger.info("Scanner: starting scan run")
        try:
            for row in SiteRepo.all():
                url, ip_override = row["url"], row["ip_override"]
                try:
                    data = get_cert_details(url, ip_override)
                    if "error" in data:
                        logger.warning("Scan error for %s: %s", url, data["error"])
                        continue
                    ResultRepo.upsert(url, data["ip"], str(data["expiry"]), data["days_left"])
                    logger.info("Scanned %s → %d days left", url, data["days_left"])
                except Exception:
                    logger.exception("Unexpected error scanning %s", url)
        except Exception:
            logger.exception("Scanner: fatal error in scan run")


def send_alerts(app):
    """Send email alerts at configured day milestones."""
    with app.app_context():
        from modules.email_utils import send_alert

        alert_days = app.config.get("ALERT_DAYS", [30, 20, 15, 10, 8, 6, 4, 3, 2, 1])
        alert_to   = app.config.get("ALERT_TO", "ops@example.com")

        logger.info("Scanner: starting alert run")
        try:
            for row in ResultRepo.all():
                site, ip, expiry = row["site"], row["ip"], row["expiry"]
                days, alert_sent = row["days_left"], row["alert_sent"]

                sent_days = set()
                if alert_sent:
                    try:
                        sent_days = {int(d) for d in alert_sent.split(",") if d.strip()}
                    except ValueError:
                        pass

                if days in alert_days and days not in sent_days:
                    try:
                        send_alert(
                            f"[SSL ALERT] {site} — {days} days left",
                            f"Site  : {site}\nIP    : {ip}\nDays  : {days}\nExpiry: {expiry}\n",
                            alert_to
                        )
                        sent_days.add(days)
                        ResultRepo.mark_alert_sent(site, sent_days)
                        logger.info("Alert sent for %s (%d days)", site, days)
                    except Exception:
                        logger.exception("Failed to send alert for %s", site)

                if days > 30 and alert_sent:
                    ResultRepo.clear_alert_sent(site)

        except Exception:
            logger.exception("Scanner: fatal error in alert run")


def _run_scheduler(app):
    interval = app.config.get("SCAN_INTERVAL_MINUTES", 5)
    schedule.every(interval).minutes.do(scan_sites, app=app)
    schedule.every().day.at("09:00").do(send_alerts, app=app)
    schedule.every().day.at("13:00").do(send_alerts, app=app)
    schedule.every().day.at("17:00").do(send_alerts, app=app)
    schedule.every().day.at("00:26").do(send_alerts, app=app)
    logger.info("Scheduler started (scan every %d min)", interval)
    scan_sites(app)
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_background_scheduler(app):
    threading.Thread(target=_run_scheduler, args=(app,), daemon=True).start()

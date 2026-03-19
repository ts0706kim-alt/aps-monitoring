# -*- coding: utf-8 -*-
"""
APS 모니터링 - 이메일 발송 모듈
"""
import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email import policy
from typing import List, Optional


def _sanitize_for_email(text: str) -> str:
    """이메일 헤더/본문에서 ASCII 인코딩 오류를 일으키는 문자 제거 (예: \\u2060 Word Joiner)"""
    if not text or not isinstance(text, str):
        return text
    # Zero-width, Word Joiner, BOM 등 제거
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)


DEFAULT_CONFIG_PATH = "email_config.json"


def load_email_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """
    이메일 설정 로드.
    환경 변수(EMAIL_*)가 있으면 우선 사용 (GitHub Actions 등 CI 환경용).
    """
    # 환경 변수에서 로드 (GitHub Actions Secrets 등)
    if os.environ.get("EMAIL_USERNAME") and os.environ.get("EMAIL_PASSWORD"):
        to_addrs = [e.strip() for e in os.environ.get("EMAIL_TO", "").split(",") if e.strip()]
        if not to_addrs:
            raise ValueError("EMAIL_TO 환경 변수에 수신자 이메일을 설정해주세요.")
        return {
            "smtp_server": os.environ.get("EMAIL_SMTP_SERVER") or "smtp.gmail.com",
            "smtp_port": int(os.environ.get("EMAIL_SMTP_PORT") or "587"),
            "use_tls": (os.environ.get("EMAIL_USE_TLS") or "true").lower() in ("1", "true", "yes"),
            "username": os.environ["EMAIL_USERNAME"],
            "password": os.environ["EMAIL_PASSWORD"],
            "from_addr": os.environ.get("EMAIL_FROM") or os.environ["EMAIL_USERNAME"],
            "to_addrs": to_addrs,
            "subject_prefix": os.environ.get("EMAIL_SUBJECT_PREFIX") or "[APS 모니터링] ",
        }

    path = os.path.abspath(config_path)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"이메일 설정 파일이 없습니다: {config_path}\n"
            f"email_config.json.example 을 복사해 email_config.json 을 만들고 "
            f"SMTP 계정 정보를 입력해주세요."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_monitoring_result_email(
    excel_path: str,
    config_path: str = DEFAULT_CONFIG_PATH,
    subject: Optional[str] = None,
) -> bool:
    """
    모니터링 결과 Excel 파일을 첨부하여 이메일 발송

    Args:
        excel_path: 첨부할 Excel 파일 경로
        config_path: 이메일 설정 JSON 파일 경로
        subject: 이메일 제목 (None이면 기본값 사용)

    Returns:
        발송 성공 여부
    """
    cfg = load_email_config(config_path)

    smtp_server = cfg.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    use_tls = cfg.get("use_tls", True)
    username = cfg["username"]
    password = cfg["password"]
    from_addr = cfg.get("from_addr", username)
    to_addrs: List[str] = cfg["to_addrs"]
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    subject_prefix = cfg.get("subject_prefix", "[APS 모니터링] ")

    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"결과 파일이 없습니다: {excel_path}")

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject_prefix = _sanitize_for_email(str(subject_prefix))
    if subject is None:
        subject = f"{subject_prefix}모니터링 결과 ({date_str})"
    subject = _sanitize_for_email(subject)

    msg = MIMEMultipart(policy=policy.SMTP)
    msg["From"] = _sanitize_for_email(from_addr)
    msg["To"] = ", ".join(_sanitize_for_email(a) for a in to_addrs)
    msg["Subject"] = subject

    body = f"""APS 모니터링 결과가 첨부되어 있습니다.

실행 일시: {date_str}

본 메일은 자동 발송되었습니다.
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Excel 첨부
    filename = _sanitize_for_email(os.path.basename(excel_path)) or "result.xlsx"
    with open(excel_path, "rb") as f:
        part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", filename))
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_bytes())
        return True
    except Exception as e:
        raise RuntimeError(f"이메일 발송 실패: {e}") from e

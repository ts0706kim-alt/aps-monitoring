# -*- coding: utf-8 -*-
"""
APS 모니터링 - 매일 실행 후 이메일 발송

1. 모니터링 실행
2. 결과 Excel 저장
3. 결과를 이메일로 발송

Windows 작업 스케줄러에서 매일 오후 12시(정오)에 실행하도록 설정하세요.
"""
import os
import sys
import time

# 스크립트 디렉토리로 이동
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 모니터링 모듈
from playwright_monitor import (
    load_targets_from_csv,
    run_monitor,
    OUTPUT_COLUMNS,
    OUTPUT_XLSX,
    INPUT_CSV,
    CONFIG_CSV,
    ensure_dir,
    DEBUG_HTML_DIR,
    DEBUG_SHOT_DIR,
)
from email_sender import send_monitoring_result_email, load_email_config


def main():
    print("=== APS 모니터링 (매일 실행 + 이메일) ===\n")

    # 1. 디렉터리 준비
    ensure_dir(DEBUG_HTML_DIR)
    ensure_dir(DEBUG_SHOT_DIR)

    # 2. 타겟 로드
    csv_path = INPUT_CSV if os.path.exists(INPUT_CSV) else CONFIG_CSV
    if not os.path.exists(csv_path):
        print(f"오류: {INPUT_CSV} 또는 {CONFIG_CSV} 파일이 없습니다.")
        sys.exit(1)

    targets = load_targets_from_csv(csv_path)
    print(f"타겟 {len(targets)}개 로드 완료\n")

    # 3. 모니터링 실행
    save_path = OUTPUT_XLSX
    df = run_monitor(targets, save_excel_path=None)

    cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
    df_out = df[cols] if cols else df
    try:
        df_out.to_excel(save_path, index=False)
    except PermissionError:
        save_path = f"aps_monitoring_result_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        df_out.to_excel(save_path, index=False)
        print(f"(기본 파일이 열려 있어 {save_path}로 저장)")

    print(f"\n엑셀 저장 완료: {save_path}")

    # 4. 이메일 발송
    try:
        send_monitoring_result_email(save_path)
        print("이메일 발송 완료.")
    except FileNotFoundError as e:
        print(f"이메일 설정 없음 (발송 건너뜀): {e}")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")
        sys.exit(1)

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()

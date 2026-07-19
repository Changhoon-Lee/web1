# V24 Portable Diversifier Overlay Lab

V24는 기존 분산 anchor처럼 V10을 Equity·Gold로 **대체하지 않습니다**. 정렬된 V10 core를 항상 100% 유지하고, 그 위에 저상관 trend sleeve를 추가합니다.

## 사전등록 Primary

```text
V10 core       +100%
Equity Trend    +30%
Gold Trend      +30%
Cash/Borrow     -60%
Net exposure    100%
Risky gross     160%
```

Primary 비중은 결과를 보고 고른 grid가 아닙니다. 허용된 추가 gross 60%를 두 diversifier에 동일 배분한 단일 고정 가설입니다.

## Secondary

- `DYNAMIC_NO_TILT_OVERLAY`: V10 100%는 고정하고 overlay 총량만 0/15/30/45/60% 상태에서 조절
- `DYNAMIC_ONLINE_OVERLAY`: core와 overlay 총량 제약을 유지한 채 Equity/Gold split만 25~75% 범위에서 조절
- 각 동적 정책은 동일 평균 overlay의 정적 50/50 control과 비교

Secondary가 실패해도 primary 결과를 변경하지 않습니다.

## 입력

일별 decimal return 파일이 필요합니다.

```csv
date,GROWTH_CRYPTO,EQUITY_TREND,GOLD_TREND,V10,CASH
2020-01-01,0.001,-0.002,0.0003,0.0011,0.00005
```

필수 열: `date`, `GROWTH_CRYPTO`, `EQUITY_TREND`, `GOLD_TREND`, `V10`

`CASH`는 선택 사항이며 없으면 0으로 처리합니다. 값 `0.01`은 하루 1% 수익입니다. 가격이나 `1` 단위의 퍼센트를 넣지 마십시오.

`V10`은 반드시 기존 공식 엔진의 **동일 날짜 일별 수익**이어야 합니다. 보고서에서는 이를 `V10_ALIGNED_COMMON_OOS`라고 부르며 `V10_FULL_HISTORY`와 혼합하지 않습니다.

## Mac 실행

압축 해제 후 폴더에서:

```bash
chmod +x *.command
export ENGINE_RETURNS_FILE="/절대경로/engine_returns.csv.gz"
./RUN_EVERYTHING.command
```

환경변수를 생략하면 현재 폴더, `~/Downloads`, `~/Documents/ZCode/Autotrade` 아래에서 입력 파일을 자동 탐색합니다.

테스트만:

```bash
./01_RUN_TESTS.command
```

전체 연구만:

```bash
./02_RUN_FULL.command
```

결과 재검증:

```bash
./VERIFY_RESULTS.command
```

## 권위 규칙

- signal은 close[t]까지의 정보만 사용
- 동적·online 목표는 t+2부터 적용
- V10 core는 portable 정책에서 항상 정확히 1,000,000 ppm
- risky gross는 최대 1,600,000 ppm
- fast down / slow up overlay hysteresis
- 실제 turnover와 cash+borrow spread 비용 포함
- exact integer ledger와 결과 SHA-256 manifest 필수
- 44 tests, 0 failed, 0 skipped가 아니면 공식 결과 금지

## 결과

```text
results/FINAL_REPORT.md
results/FINAL_GATE.json
results/FEASIBILITY_SCREEN.json
results/strategy_summary.csv
results/bootstrap_results.csv
results/hac_results.csv
results/DSR_RESULTS.json
results/stress_tests.csv
results/*_exact_ledger.csv.gz
results/OUTPUT_MANIFEST.json
runtime/V24_ZCode_Handoff.zip
```

## 판정 한계

역사적 경제·통계 gate를 모두 통과해도 최고 상태는:

```text
HISTORICAL_PORTABLE_OVERLAY_PARETO_PASS_NEEDS_NEW_OOS
```

입니다. 이 패키지는 live readiness를 주장하지 않으며, 외부 데이터 provenance와 공식 V10 full-history ledger 검증을 대신하지 않습니다.

# V23.1 Final Pareto Audit Lab

단 하나의 입력 패널로 V10 정렬 기준선, 분산 anchor, 정적 1.60배, 동적 risk budget, bounded online tilt를 동일 비용·지연 규칙에서 비교하는 최종 감사 패키지입니다.

## 연구 가설

1. 분산 anchor가 충분히 낮은 위험을 만들면 제한된 포트폴리오 레버리지로 V10의 절대수익을 회복할 수 있는가?
2. 정적 1.60배가 역사적 Pareto 후보인가?
3. 동적 risk controller가 동일 평균 레버리지 정적 통제보다 가치를 추가하는가?
4. bounded online tilt가 no-tilt 동적 정책보다 가치를 추가하는가?

## 입력

```csv
date,GROWTH_CRYPTO,EQUITY_TREND,GOLD_TREND,V10,CASH
2020-01-01,0.001,-0.002,0.0003,0.0011,0.00005
```

`CASH`는 선택이며 없으면 0으로 처리합니다. 가격이나 퍼센트가 아니라 일별 소수 수익률이어야 합니다.

자동 탐색 순서:

1. `--input`
2. `ENGINE_RETURNS_FILE`
3. 현재 폴더, `~/Documents/ZCode/Autotrade`, `~/Downloads`의 `engine_returns.csv[.gz]`
4. 해당 위치의 `V23*Handoff*.zip` 내부 engine returns

## 실행

```bash
chmod +x *.command
./RUN_EVERYTHING.command
```

공식 bootstrap은 비교별·block별 20,000회입니다. 진단 실행만 줄일 수 있습니다.

```bash
V23_BOOTSTRAP_SAMPLES=1000 ./02_RUN_FULL.command
```

## 권위 구현

- `src/v23_core.py`: 최초 완성 코어, 감사 가능한 원본
- `src/v23_final_lab.py`: 권위 wrapper
  - 실제 t+2 delayed position·turnover·financing으로 controller equity 갱신
  - 모든 Mac 실행 명령을 handoff ZIP에 포함

## 전략

- `V10_ALIGNED_COMMON_OOS`
- `UNIFORM_1X`
- `ANCHOR_1X`: 20/60/120일 최대 EWMA 변동성의 역수, 가중치 20~50%
- `STATIC_130`, `STATIC_145`, `STATIC_160`
- `DYNAMIC_NO_TILT`
- `DYNAMIC_ONLINE_TILT`
- 동적 정책별 동일 평균 레버리지 정적 진단

## 인과성

- close[t]까지 신호 계산
- t+2부터 목표 적용
- 온라인 update는 관측된 engine return만 사용
- 미래 행 변경 시 과거 anchor·tilt·controller equity·leverage가 불변인 검사 포함

## 출력

`results/`에 전략별 일간 수익, 포지션, exact integer ledger, risk-capacity attribution, feasibility, bootstrap, HAC, DSR, fold, stress, baseline identity와 manifest를 생성합니다.

최종 전달본:

```text
runtime/V23_1_ZCode_Handoff.zip
```

## 판정 한계

정적 1.60배가 모든 gate를 통과해도 반복 연구에 사용된 역사이므로 `HISTORICAL_STATIC_160_PARETO_PASS_NEEDS_NEW_OOS`까지만 허용합니다. 입력 engine returns의 생성·provenance와 외부 공식 V10 full-history ledger 동일성은 별도 원장으로 검증해야 합니다.

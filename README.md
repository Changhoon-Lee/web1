# V23.1 Final Pareto Audit Lab

단 하나의 입력 패널로 V10 정렬 기준선, 분산 anchor, 정적 1.60배, 동적 risk budget, bounded online tilt를 동일 비용·지연 규칙에서 비교하는 최종 감사 패키지입니다.

## 연구 가설

1. 분산 anchor가 충분히 낮은 위험을 만들면 제한된 포트폴리오 레버리지로 V10의 절대수익을 회복할 수 있는가?
2. 정적 1.60배가 역사적 Pareto 후보인가?
3. 동적 risk controller가 동일 평균 레버리지 정적 통제보다 가치를 추가하는가?
4. bounded online tilt가 no-tilt 동적 정책보다 가치를 추가하는가?

## 입력

다음 열을 가진 일별 decimal return CSV/CSV.GZ가 필요합니다.

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

빠른 확인:

```bash
./01_RUN_TESTS.command
```

Full bootstrap 기본값은 비교별·block별 20,000회입니다. Mac 부하를 낮추려면 진단 실행에서만:

```bash
V23_BOOTSTRAP_SAMPLES=1000 ./02_RUN_FULL.command
```

공식 결과는 20,000회로 다시 실행하십시오.

## 핵심 전략

- `V10_ALIGNED_COMMON_OOS`
- `UNIFORM_1X`
- `ANCHOR_1X`: 20/60/120일 최대 EWMA 변동성의 역수, 가중치 20~50%
- `STATIC_130`, `STATIC_145`, `STATIC_160`
- `DYNAMIC_NO_TILT`: 변동성·ES·상관 floor·gap margin·drawdown capacity의 최소값
- `DYNAMIC_ONLINE_TILT`: anchor ±10%p 이내 portfolio-level mirror descent
- 각 동적 정책의 동일 평균 레버리지 정적 진단

## 인과성

- close[t]까지 신호 계산
- 가장 빠른 t+2에서 목표 적용
- 온라인 업데이트는 이미 관측된 engine return만 사용
- 미래 행 변경 시 과거 온라인 weight가 변하지 않는 테스트 포함

## 출력

`results/` 아래에 전략별 일간수익, 포지션, exact integer ledger, capacity attribution, feasibility, bootstrap, HAC, DSR, fold, stress, baseline identity, manifest가 생성됩니다.

최종 전달본:

```text
runtime/V23_1_ZCode_Handoff.zip
```

## 판정 원칙

정적 1.60배가 경제·통계 gate를 통과해도 이미 반복 연구에 사용된 역사이므로 상태는 `HISTORICAL_STATIC_160_PARETO_PASS_NEEDS_NEW_OOS`까지만 허용합니다. 동적 또는 온라인 정책은 더 단순한 no-tilt·equal-average-leverage 통제를 이기지 못하면 제거합니다.

## 한계

이 패키지는 입력 engine returns의 생성 과정을 대신 검증하지 않습니다. `BASELINE_IDENTITY.json`은 정렬 OOS 기준선을 기록하지만 외부 공식 V10 전체-history ledger와 자동 동일성을 주장하지 않습니다. ZCode는 원본 engine/provenance manifest를 함께 보존해야 합니다.

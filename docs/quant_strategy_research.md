# Quant Strategy Research Notes

Version: 0.4.0-quant

이 문서는 실행 코드의 수학적 근거와 한계를 기록한다. 논문 결과를 그대로 복제한 전략이 아니라,
검증된 현상을 단순하고 설명 가능한 형태로 구현한 초기 모델이다.

## 1. 한국 주식

한국 개별주식에서는 미국식 전통 가격 모멘텀을 그대로 적용하기 어렵다.

- Sim, Kang, Kim & Lee (2022), *The Momentum Strategies and Salience: Evidence from the Korean Stock Market*:
  전통 모멘텀은 부진하고 장기 반전에 취약한 반면 rank/sign momentum은 더 안정적인 성과를 보였다고 보고한다.
  DOI: 10.1080/1540496X.2022.2034615
- Eom & Park (2021), *A Study on the Momentum Effect of the Korean Stock Markets Using Principal Component Analysis*:
  한국 시장에서 음의 모멘텀 이익이 견고하게 관찰된다고 보고한다.
  DOI: 10.22510/kjofm.2021.38.1.005
- Chen, Chou, Ko & Rhee (2021), *Non-parametric momentum based on ranks and signs*:
  일별 수익률의 rank/sign 기반 모멘텀이 극단적인 과거 가격 움직임에 덜 민감하고 crash/reversal에 더 강건하다고 보고한다.
  DOI: 10.1016/j.jempfin.2020.11.004

따라서 주식 핵심 신호는 누적수익률 자체보다 **상승일 빈도(Sign Momentum)** 를 크게 반영한다.

Sign_n = positive non-zero daily returns / non-zero daily returns × 100

StockScore =
0.30 × Sign60
+ 0.20 × Sign20
+ 0.20 × Trend
+ 0.15 × RiskAdjustedMomentum20
+ 0.10 × Stability
+ 0.05 × VolumeConfirmation
- SaliencePenalty

후보군 선정도 큰 누적수익률 하나가 순위를 지배하지 않도록 유동성 + Sign60/Sign20을 중심으로 구성한다.

## 2. 암호화폐

- Liu & Tsyvinski (2021), *Risks and Returns of Cryptocurrency*:
  암호화폐에서 강한 time-series momentum 및 attention 기반 예측력을 보고한다.
  DOI: 10.1093/rfs/hhaa113
- Liu, Tsyvinski & Wu (2022), *Common Risk Factors in Cryptocurrency*:
  market, size, momentum 요인이 암호화폐 횡단면 기대수익을 설명하는 핵심 요인이라고 보고한다.
  DOI: 10.1111/jofi.13119
- Tzouvanas, Kizys & Tsend-Ayush (2020), *Momentum trading in cryptocurrencies*:
  단기 모멘텀은 강하지만 장기에서는 약해진다고 보고한다.
  DOI: 10.1016/j.econlet.2019.108728
- Dobrynskaya (2023), *Cryptocurrency Momentum and Reversal*:
  약 2~4주 단기 모멘텀과 그보다 긴 구간에서의 반전 효과를 보고한다.

따라서 코인은 7일/21일을 핵심으로 사용하고 42일 과열은 감점한다.

CryptoScore =
0.40 × RiskAdjustedMomentum21
+ 0.30 × RiskAdjustedMomentum7
+ 0.15 × Trend
+ 0.10 × Stability
+ 0.05 × VolumeConfirmation
- ReversalPenalty

## 3. 공통 위험조정

기간 수익률:
R_n = P_t / P_(t-n) - 1

변동성 정규화:
Z_n = R_n / (sigma × sqrt(n))

모멘텀 점수:
MomentumScore_n = 50 + 25 × clip(Z_n, -2, 2)

정량 방향:
- score >= 65: BUY candidate
- score <= 35: SELL candidate
- otherwise: HOLD

AI는 정량 방향을 반대로 바꾸지 않는다.
- BUY -> BUY 또는 HOLD
- SELL -> SELL 또는 HOLD
- HOLD -> HOLD

즉 AI는 뉴스/거시/데이터 품질을 이용한 **veto layer** 다.

## 4. Position sizing

Barroso & Santa-Clara (2015), Moreira & Muir (2017)의 변동성 관리 아이디어를 참고하되
저변동성 자산을 레버리지하지 않고 고변동성에서만 노출을 줄인다.
Cederburg et al. (2020)은 변동성 관리의 우위가 실시간 out-of-sample에서는 체계적으로 유지되지 않을 수 있다고 지적하므로,
본 앱에서는 이를 수익원으로 보지 않고 **고변동성 시 주문 크기를 줄이는 안전장치**로만 사용한다.

RiskScale = clip(TargetDailyVol / RealizedDailyVol, 0.35, 1.0)

- Stock target daily vol: 2%
- Crypto target daily vol: 4%
- BuyNotional = BaseBuyPct × RiskScale × Equity

이는 연구 결과를 그대로 복제한 최적값이 아니다. 보수적인 초기 운영값이다.

## 5. 검증 원칙

금융 연구에는 데이터 마이닝과 백테스트 과최적화 위험이 크다.
따라서 다음을 전략 변경의 필수 조건으로 둔다.

- Paper 우선
- 거래비용/슬리피지 포함
- 동일 데이터에서 탐색과 검증을 반복하지 않기
- walk-forward / out-of-sample 검증
- 단일 거래나 소표본으로 임계값 변경 금지
- 수학 가중치/임계값 변경은 Markdown 제안이 아니라 코드 버전 + 테스트로만 반영

Harvey, Liu & Zhu (2016)는 다중검정으로 인해 많은 factor 발견이 거짓일 수 있음을 지적한다.
또한 최근 연구는 volatility management의 우위가 out-of-sample 및 거래비용 반영 후 항상 유지되는 것은 아니라고 보고한다.
따라서 본 전략을 '검증된 수익 보장 전략'으로 취급하지 않는다.

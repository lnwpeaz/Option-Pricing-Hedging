# Asian option Monte Carlo: ทำอะไร ได้อะไร และใช้ต่ออย่างไร

V2-A เพิ่มเครื่องมือคิดราคา Asian options และเปรียบเทียบ Monte Carlo 5 วิธีแล้ว
การทดลองเต็มเก็บ **2,880 estimates**, **18,432 ราคาแยกตาม scramble**,
82,575,360 production paths และ 294,912 pilot paths ไม่มี estimate ล้มเหลว
เฉพาะ primary estimates สร้าง normal coordinates 2,387,607,552 ค่า
(ไม่รวม reference/benchmark/warm-up/validation/replay)
ใช้เวลารันชุดหลักประมาณ 153 วินาที
บนเครื่องและ environment ที่บันทึกไว้ เวลานี้รวมงานอ้างอิง/วิเคราะห์/benchmark
ไม่ใช่เวลาคิดราคา option หนึ่งสัญญา และไม่รับประกันเครื่องอื่นจะได้เวลาเดียวกัน

อ่านผลเต็มที่ [RESULTS.md](../reports/examples/v2-asian/RESULTS.md)
และ [ข้อมูลดิบ](../reports/examples/v2-asian/estimates.csv)

## ภาพที่เรากำลังจำลอง

Asian option ใช้ **ราคาเฉลี่ยตามวันสังเกต** มาคิด payoff แทนการดูวันสุดท้ายอย่างเดียว
เช่น put มีราคาใช้สิทธิ K=125 และราคาที่สังเกตสามครั้งเป็น 110,118,126
ค่าเฉลี่ยเท่ากับ 118 จึงได้เงินตอนหมดอายุ max(125−118,0)=7 ต่อหนึ่งหน่วย
ถ้า r=4% และหมดอายุในครึ่งปี มูลค่าปัจจุบันของ payoff เส้นทางนี้ประมาณ 6.8614
ราคาเริ่มต้น S0 ไม่ใช่อีกหนึ่ง observation ที่เอาไปรวมเฉลี่ย

ตอนเริ่มต้นเราไม่รู้เส้นทางอนาคต จึงสร้างหลายเส้นทางภายใต้ risk-neutral GBM
คิด discounted payoff แต่ละเส้นทาง แล้วประมาณค่าเฉลี่ย
นี่คือการประมาณ **ราคาในโมเดล** ไม่ใช่ทำนายว่าหุ้นจะขึ้นเท่าไรหรือกำไรลงทุนจะเป็นเท่าไร
วันสังเกตเป็นส่วนหนึ่งของสัญญา เปลี่ยน 12 เป็น 52 ครั้งจึงเปลี่ยนสัญญาที่คิดราคา

## ห้าวิธีต่างกันตรงไหน

| วิธี | วิธีทำ | หน่วยอิสระที่ใช้คำนวณ SE |
|---|---|---|
| plain | สุ่มเส้นทางตามปกติ | N discounted payoffs |
| antithetic | ใช้ normals z คู่กับ −z แล้วเฉลี่ยเป็นคู่ | N/2 ค่าเฉลี่ยคู่ |
| control | ใช้ geometric-average payoff ที่รู้ expected value ช่วยลด noise | N adjusted payoffs; มี pilot แยกเพิ่ม |
| sobol | กระจายจุดด้วย scrambled Sobol และใช้ Brownian increments | R ราคาจาก scramble อิสระ |
| sobol_bridge | ใช้ Sobol ชุดเดียวกับวิธีก่อน แต่สร้าง W_T ก่อนแล้วเติมจุดกลาง | R ราคาจาก scramble อิสระ |

control มีการประมาณ beta จาก pilot 512 เส้นทางแล้วตรึงไว้ ก่อนสุ่ม production ชุดใหม่
นี่เป็นการประมาณค่าสถิติ ไม่ต้องเทรน neural network หรือหา label ราคาจากตลาด
Geometric payoff ใช้ค่าเฉลี่ยเรขาคณิตซึ่งมีสูตรราคาและตรวจเทียบด้วยการอินทิเกรตอิสระแล้ว

Sobol ใช้ R=16 scrambles และ 2^p จุดต่อ scramble, bits=52
จุดใน scramble เดียวกันไม่เป็น IID จึงห้ามเอาทุก payoff มาคิด SE แบบ plain MC
ช่วง 95% ของ QMC เป็น Student-t approximation จาก 16 ราคา ใช้ 15 degrees of freedom
ส่วน plain/antithetic/control ใช้ normal approximation ไม่มีการบังคับ CI ให้อยู่เหนือศูนย์
ถ้าตัวอย่าง payoff เป็นศูนย์ทั้งหมด จะมี zero_observed_variance เตือนว่าอาจพลาด rare payoff
ต่างจาก sigma=0 ที่เป็น deterministic จริงและไม่ใช้ RNG เลย

## ผลวัดจริงที่อ่านได้อย่างมั่นใจ

ตัวอย่างสัญญา S0=100,K=100,r=5%,sigma=20%,52 fixings ในหนึ่งปี
N=65,536, ทำซ้ำอิสระ 32 ครั้ง:

| วิธี | SD ของราคาข้ามการทำซ้ำ | Median เวลาต่อ estimate ที่ batch=1024 |
|---|---:|---:|
| plain | 0.029553 | 0.0432 วินาที |
| antithetic | 0.023030 | 0.0401 วินาที |
| control | 0.000987 | 0.0461 วินาที |
| sobol | 0.005237 | 0.1237 วินาที |
| sobol_bridge | 0.001049 | 0.1369 วินาที |

control ให้การกระจายของราคาประมาณแคบลง 30 เท่า และ Sobol bridge ประมาณ 28 เท่า
เทียบกับ plain **ในกรณีนี้** นี่คือผลด้าน sampling variability ไม่ใช่หลักฐานว่า
ราคาทั้งสองแม่นกว่าตลาด 30 เท่า หรือวิธีใดดีที่สุดกับทุก payoff
Sobol bridge ใช้เวลามากกว่า control ใน benchmark นี้ ความซับซ้อนของชื่อวิธีจึงไม่ใช่เกณฑ์เลือก

ที่ batch=1024 peak traced allocations ของ plain ประมาณ 2.05 MiB,
control 2.07 MiB และ Sobol ทั้งสองประมาณ 6.53 MiB
เป็น tracemalloc คนละรอบกับการจับเวลา ไม่ใช่ RAM/RSS ทั้ง process
Sobol เก็บจุดและ normals หนึ่ง scramble จึงไม่ใช่ O(batch) memory ทั้งวิธี
ดู [benchmark.csv](../reports/examples/v2-asian/benchmark.csv) และ
[allocations.csv](../reports/examples/v2-asian/allocations.csv) สำหรับทุกการวัดจริง

## ข้อค้นพบสำคัญ: ตัวอ้างอิงเองยังไม่ละเอียดพอ

QuantLib 1.44 ถูกตรึงเวอร์ชันและตรวจวันสังเกต ACT/365F ทีละวัน
เปรียบเทียบ finite difference 3 grids, Choi 3 ระดับ และ MC-control อีก 4 seeds
แต่ **ทั้ง 6 สัญญามี empirical reference radius เกินเป้า 0.0005**
ทุก 90 method/budget cells จึงงด precision-dependent ranking ตามเกณฑ์ที่ตั้งก่อนทดลอง
ไม่ได้เปลี่ยน engine, grid หรือ seed หลังเห็นผลเพื่อให้ดูผ่าน

ในตัวอย่าง 52 fixings,K=100 ราคา Choi ระดับสุดท้ายเป็น 5.837290
reference radius ประมาณ 0.008267 ขณะที่ FD ที่ละเอียดที่สุดประมาณ 5.844275
และ external MC-control อยู่ใกล้ 5.844 ผล control ของเราเฉลี่ยประมาณ 5.843858
ความต่างนี้ชี้ว่าราคาอ้างอิงเป็นคอขวด; ไม่ใช่หลักฐานว่าราคาของเราผิดระดับ 0.0066
และไม่ทำให้ external MC กลายเป็น exact truth

RMSE ในรายงานเป็นค่าที่เทียบกับจุดอ้างอิงที่ประกาศ จึงยังอ่านเป็น approximate RMSE
ช่วง sensitivity ของ RMSE สมมติให้ reference band ครอบคลุมค่าจริง ไม่ใช่ CI ใหม่
Possible coverage หมายถึง CI แตะ reference band; definite coverage หมายถึงครอบคลุมทั้ง band
เช่น control มี possible coverage 100% แต่ definite coverage 0% ในกรณีข้างต้น
จึงยังสรุปไม่ได้จากตารางนี้ว่าช่วง 95% สอบเทียบได้สมบูรณ์

## ใส่สัญญาของตัวเองและได้อะไร

แก้ [asian_custom.toml](../configs/asian_custom.toml): spot, strike, r, sigma, call/put
และ fixing_times โดยเวลาเป็นปี ต้อง 0<t1<...<tm และ observation สุดท้ายคือวันหมดอายุ

```sh
export PYTHONPATH="$PWD/src"
.venv/bin/python -m pip install -r requirements-research.txt
.venv/bin/python -m option_hedging.experiments.asian_study \
  --config configs/asian_custom.toml --output-dir reports/runs/my-asian-run
```

โฟลเดอร์ปลายทางต้องยังไม่มีอยู่ เพื่อเก็บหลักฐานเดิมไว้
ผลที่ได้คือราคา, SE, CI, pilot beta, งานคำนวณ, diagnostic, CSV/กราฟ/รายงานและ source snapshot
ไม่จำเป็นต้องติดตั้ง QuantLib เพื่อใช้ pricing API; หากไม่มี comparator จะรายงาน unavailable

ตัวอย่างที่รันแล้วใช้ S0=120,K=125,r=4%,sigma=25%, arithmetic put,
fixings=(.1,.25,.5): เก็บครบ 480 estimates ไม่มีล้มเหลว
ค่าเฉลี่ยของ control ที่ N=65,536 ประมาณ **7.297504 ต่อหนึ่งหน่วย**
ตัวอย่าง macro repeat0 ได้ 7.298485 และ approximate 95% CI [7.296687,7.300282]
เป็นช่วงความไม่แน่นอนจากการคำนวณของ repeat นั้น ไม่ใช่ช่วงราคา option ในตลาด

ตารางเวลาตัวอย่างนี้ใช้กับ date-based QuantLib reference ไม่ได้ตรงทุกวัน
ระบบจึงคงผล pricing แต่แสดง unavailable สำหรับ arithmetic reference และไม่ให้ RMSE ranking
ไม่ปัดวันสังเกตให้ตรงเอง ดู [ตัวอย่างครบชุด](../reports/examples/v2-asian-custom/RESULTS.md)

ใช้ API โดยตรงเมื่อต้องการผลเพียงครั้งเดียว:

```python
import numpy as np
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_monte_carlo import price

spec = AsianOptionSpec(120,125,.04,.25,'put',(.1,.25,.5))
result = price(spec,n_paths=65536,method='control',rng=np.random.default_rng(42))
print(result.price,result.standard_error,result.ci_low,result.ci_high)
```

## หลักฐานและสิ่งที่ต่อยอดได้

ชุดตรวจอัตโนมัติหลังแก้ประเด็นรีวิวผ่าน **529 ข้อ** ทั้งของเดิมและของใหม่
รีวิวอิสระพบ 4 ประเด็นสำคัญและกรณี variance เล็กมากอีกหนึ่งเรื่อง
เพิ่ม regression tests ที่ล้มเหลวก่อนแก้แล้วตรวจผ่านครบ รวม failed-only benchmark plots
รายละเอียดอยู่ใน [review findings](../reports/verification/asian-execution/review-findings.md)
[Independent audit](../reports/verification/v2-asian-checks.json) ตรวจซ้ำ 32,106 เงื่อนไขตัวเลข
จากข้อมูลที่บันทึก รวม QMC 1,152 estimates, pilot beta 576 ชุด, metrics 90 cells
และ paired comparisons 90 ชุด โดยไม่เรียกฟังก์ชันสรุปสถิติชุดเดียวกับที่สร้างรายงาน
ยังมี geometric/single-fixing/put/irregular/sigma=0/rare-payoff checks นอก primary grid
ตรวจ source/hash และกู้ซอร์สมารันใหม่จริงแยกจากการตรวจไฟล์
[Replay proof](../reports/verification/v2-asian-replay.json) ยืนยัน numerical/input artifacts
9 ไฟล์ตรงกันทุกไบต์ โดยตรวจ actual imported module path ว่าอยู่ใน recovered/src จริง

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q -W error
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/examples/v2-asian
PYTHONPATH=src .venv/bin/python reports/verification/audit_asian.py \
  reports/examples/v2-asian reports/verification/my-asian-checks.json
```

คุณค่าด้าน Computer Engineering คือแยก pure transforms/kernel จาก RNG,
จัด independent streams/pairing, stable centered/scaled moments, batching,
measured time/allocation trade-offs, strict configs และ recoverable numerical experiments
ด้าน Financial Engineering คือ payoff conventions, risk-neutral pricing, variance reduction,
uncertainty calibration และการตรวจ numerical reference risk

ใช้งานเป็น research/pricing component ในขอบเขตโมเดลนี้ได้แล้ว
ก่อนใช้ตัดสินใจเกี่ยวกับเงินจริงยังต้องมีสัญญาตลาดที่ตรงกัน, market inputs/calibration,
exercise/dividend conventions และการตรวจ model/operational risk ที่เกี่ยวข้อง
ไม่ได้เพิ่ม American stock/ETF options, portfolio allocation หรือ broker execution ในชิ้นนี้

ขั้นต่อไปที่มีเหตุผลคือทำ reference convergence เพิ่มตาม protocol ที่ประกาศล่วงหน้า
เพื่อแยก sampling error ออกจาก reference error ให้ละเอียดพอ ก่อนอ้าง ranking
ส่วน jump-risk hedging และ contract-aware quote/IV ยังเป็น V2-B/V2-C ที่แยกขอบเขตไว้

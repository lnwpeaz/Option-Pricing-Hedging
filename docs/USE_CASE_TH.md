# ใช้งานโปรเจกต์นี้อย่างไรให้ได้คำตอบที่นำไปใช้ต่อได้

เป้าหมายของโปรเจกต์นี้คือ **เครื่องมือวิจัยราคา options และความเสี่ยงจากการ hedge**
พร้อมหลักฐานด้าน numerical computing และ Computer Engineering
ส่วนการเลือกหุ้น จัดสัดส่วน ETF และเปรียบเทียบพอร์ตเป็นงาน Portfolio Quantitative
Research อีกโครงการหนึ่ง ไม่ได้เพิ่มเข้ามาในงานนี้

## ใช้งานที่รองรับตอนนี้

1. ใส่เงื่อนไข European option และสมมติฐาน แล้วคำนวณราคา call/put และ Greeks
2. เปรียบเทียบ Monte Carlo estimators ว่าคลาดเคลื่อนเท่าไร ใช้งานคำนวณเท่าไร
   และช่วงความเชื่อมั่นน่าเชื่อถือแค่ไหนในกรณีที่ทดลอง
3. ถ้าศึกษาฝั่งขาย call จำลอง delta hedge แล้ววัด P&L, RMSE, ต้นทุนและเงินสด
   เมื่อเปลี่ยนความถี่ซื้อขายหรือความผันผวนที่ใช้
4. เปิดบัญชีแต่ละเหตุการณ์ ดูสมมติฐาน เก็บผล และรันซ้ำเพื่อตรวจงาน

จึงใช้งานเป็น numerical/scenario research tool ได้แล้วภายในขอบเขตที่ตรวจไว้
การได้ราคาจากโมเดลยังไม่ได้บอกว่า option ตลาดถูกหรือแพง หรือควรเปิดสถานะจริง

## ตัวอย่างใหม่ที่รันจริง

เป็นสัญญาสมมติ ไม่ใช่ราคาตลาดหรือสินทรัพย์ในพอร์ตของคุณ:

| Input | ค่า |
|---|---:|
| ราคา underlying | 120 |
| ราคาใช้สิทธิ | 125 |
| อายุคงเหลือ | 0.5 ปี |
| ดอกเบี้ยต่อปีแบบ continuous | 4% |
| volatility สำหรับตั้งราคา | 25% ต่อปี |
| เงินปันผล | 0 ตามขอบเขตโมเดล |
| ลักษณะสัญญา | European, payoff จำลองหนึ่งหน่วย |

ผลจาก `reports/examples/contract-review/pricing/baseline.csv`:

| Output | Call | Put |
|---|---:|---:|
| ราคาโมเดล | 7.337356 | 9.862190 |
| Delta | 0.488273 | -0.511727 |
| Gamma | 0.018798 | 0.018798 |
| Vega ต่อ volatility เพิ่ม 1 percentage point | 0.338367 | 0.338367 |

ตัวอย่างการอ่าน: call มี delta ประมาณ 0.488 หมายถึงความไวเฉพาะบริเวณปัจจุบัน
ถ้า spot เพิ่มเล็กน้อย 1 หน่วย ราคา call จะเพิ่มประมาณ 0.488 หน่วยเมื่อสิ่งอื่นคงเดิม
gamma บอกว่า delta เปลี่ยนตาม spot; ไม่ควรใช้ delta ตัวเดียวกับการเปลี่ยนราคาครั้งใหญ่
vega บอกว่าการเปลี่ยนสมมติฐาน volatility มีผลต่อราคาเพียงใด
ตัวเลขเหล่านี้เป็นความไวของโมเดล ไม่ใช่คำรับรองราคาที่ซื้อขายได้

## Monte Carlo คำนวณสัญญาใหม่นี้ได้ดีแค่ไหน

รันอีกชุดผ่าน engine เดิม: 3 sample sizes, 3 strikes, call/put,
3 estimators และ 32 independent repeats ต่อกรณี รวม 1,728 estimates
ผล call ที่ strike 125 และ 65,536 production evaluations:

| วิธี | RMSE ของราคา | ช่วง 95% ของ RMSE | Work-normalized gain เทียบ plain |
|---|---:|---|---:|
| Plain | 0.059768 | [0.044460, 0.074456] | 1.00 |
| Antithetic | 0.037261 | [0.029238, 0.044454] | 2.57 |
| Control variate | 0.027253 | [0.021917, 0.032110] | 4.74 |

RMSE นี้วัดความคลาดเคลื่อนจากราคา Black-Scholes ภายใต้โมเดลเดียวกัน
ไม่ใช่ความคลาดเคลื่อนจากราคาตลาด ช่วงดังกล่าวเป็น bootstrap ของผลแต่ละ repeat
control ใช้ pilot เพิ่ม 1,024 evaluations และนับงานนั้นแล้วใน work gain
ระดับประโยชน์เปลี่ยนจากสัญญามาตรฐานเดิม จึงไม่ควรอ้างว่าได้ gain เท่ากันทุกสัญญา

หลักฐานทั้งหมดอยู่ใน `reports/examples/contract-review/monte-carlo/`
รวม raw estimates, metrics, seed keys, benchmarks, กราฟ, config และ source snapshot

## ถ้า volatility ที่เกิดในสถานการณ์สูงกว่าที่ใช้ตั้งราคา

สร้างสถานการณ์ true sigma=30%, mu=6% ซึ่งเป็นสมมติฐานทดสอบที่เรากำหนดเอง
ใช้ 3,000 common paths, 126 ช่วงเวลา และ 500 shared bootstrap resamples
รวม 21 กรณีและ 63,000 case/path outcomes

เพื่อเทียบ policy อย่างเป็นธรรม ตารางนี้ตรึงเงิน premium ที่รับไว้เท่ากัน
ตามราคา reference sigma=25%; ทุกแถวคิดต้นทุน 2 bps ต่อ traded notional:

| Sigma ของ hedge | ปรับทุกกี่ขั้น | Mean P&L | RMSE | ช่วง 95% ของ RMSE | Mean financed cost |
|---|---:|---:|---:|---|---:|
| 25% | 1 | -1.875338 | 2.213391 | [2.168406, 2.261765] | 0.120305 |
| 25% | 5 | -1.772391 | 2.606656 | [2.515056, 2.679016] | 0.067709 |
| 30% | 1 | -1.853477 | 2.037382 | [2.006697, 2.067414] | 0.112665 |
| 30% | 5 | -1.760289 | 2.492367 | [2.424447, 2.546285] | 0.064695 |

สิ่งที่ใช้ประกอบการตัดสินใจในสถานการณ์นี้ได้:

- ซื้อขายถี่ขึ้นลด RMSE ที่สังเกตได้ แต่จ่ายต้นทุนเพิ่ม ไม่ได้ทำให้ mean P&L ดีที่สุด
- ต่อให้รู้ sigma ที่ใช้สร้างสถานการณ์และ hedge ให้ตรง ก็ยังมี mean P&L ติดลบ
  เมื่อรับ premium ตาม sigma ที่ต่ำกว่า จึงต้องดูทั้งราคาเริ่มต้นและความเสี่ยงของ policy
- การตั้งเป้า RMSE ต่ำสุด ต่างจากกำไรเฉลี่ยสูงสุดหรือต้นทุนต่ำสุด
  ต้องระบุเป้าหมายก่อนเปรียบเทียบ และอ่าน paired intervals ในผลฉบับเต็ม
- เงินทั้งหมดเป็นหน่วยของ short option จำลอง ไม่ใช่เปอร์เซ็นต์ผลตอบแทน
  หรือขนาดความเสี่ยงที่พอร์ตหุ้นของคุณลดลง

ผลเต็มอยู่ใน `reports/examples/contract-review/hedging/` ทั้ง model-premium และ
common-premium basis พร้อม ledger ของหนึ่งเส้นทางและรายละเอียดทุกกรณี

นำ source snapshots ของตัวอย่าง pricing/hedging นี้ออกมารันผ่าน CLI ซ้ำแล้ว
ไฟล์ numerical ที่เลือกตรวจทั้ง14ไฟล์ตรงทุกไบต์ใน environment เดิม
หลักฐานอยู่ใน `reports/verification/contract-review-replay.json`
ส่วน MC ใหม่ตรวจค่า bias/RMSE/coverage จาก raw estimates และ integrity ของไฟล์
ไม่ได้อ้างว่า timing ทำซ้ำได้ตรงกันหรือผ่านการทดสอบข้ามแพลตฟอร์ม

## ทดลองเปลี่ยน input เอง

จาก project root ให้คัดลอก config ตัวอย่างแล้วเปลี่ยนค่าในขอบเขตที่รองรับ
แต่ละคำสั่งต้องเลือก output directory ใหม่; engine ปฏิเสธการเขียนทับผลเดิม

```sh
export PYTHONPATH=src
export MPLCONFIGDIR=/private/tmp/option-hedging-mpl-cache
export XDG_CACHE_HOME=/private/tmp/option-hedging-cache

.venv/bin/python -m option_hedging.experiments.pricing_demo \
  --config configs/contract_review_pricing.toml \
  --output-dir reports/runs/my-contract-pricing

.venv/bin/python -m option_hedging.experiments.monte_carlo_demo \
  --config configs/contract_review_monte_carlo.toml \
  --output-dir reports/runs/my-contract-mc

.venv/bin/python -m option_hedging.experiments.runner \
  --config configs/contract_review_hedging.toml \
  --output-dir reports/runs/my-contract-hedge

.venv/bin/python -m option_hedging.experiments.verify_run \
  reports/runs/my-contract-hedge
```

`pricing_demo` ใช้เฉพาะ `[option]`; ส่วน runner ใช้ market/simulation/hedge_grid/
uncertainty ตาม schema ของตัวเอง ไม่ได้อ่าน config ของอีกโปรแกรมโดยอัตโนมัติ
`physical_drift` และ `true_volatility` เป็นสถานการณ์ที่คุณป้อน ไม่ใช่ค่าที่ระบบ
คาดการณ์หรือประมาณจาก ticker ให้แล้ว ดู `RESULTS.md` และ `effective_config.json`
ของแต่ละ run ควบคู่กับ CSV

## จะต่อยอดให้แตะข้อมูลตลาดจริงตรงไหน

ขั้นที่ตรงกับตัวตนโปรเจกต์คือ **option quote diagnostics และ implied volatility**:
ตรวจชนิดสัญญา เวลา quote, bid/ask และขอบเขตราคา แล้วหาค่า volatility ที่ทำให้
ราคาโมเดลสอดคล้องกับ quote พร้อม Greeks, sensitivity และ quality flags
ส่วนนี้ยังไม่ได้ implement และยังไม่ใช่สัญญาณว่าควรซื้อ/ขาย

ต้องกำหนดประเภทสัญญาที่รองรับก่อน: โมเดลตอนนี้ไม่มี dividends หรือ American
exercise และไม่มี margin/execution ส่วน equity options สหรัฐฯ มีรายละเอียด
แตกต่างจากโมเดล เช่น American exercise และการส่งมอบหุ้น ตาม
[OCC](https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications)
การคูณผลด้วย 100 อย่างเดียวจึงไม่ทำให้ครบกลไกสัญญาจริง

ถ้าจะสร้างขั้นนี้ ต้องออกแบบและตรวจ solver, price bounds, หน่วย, การ reject
ข้อมูลที่ใช้ไม่ได้ และกรณีที่ IV ไม่มีคำตอบ/ระบุค่าไม่ได้ ก่อนนำ quote มาตีความ
นี่เป็นเส้นทางต่อยอดของ pricing/risk engine โดยไม่ทับกับการจัดพอร์ตหุ้น

## สิ่งที่นำไปแสดงในโปรไฟล์ได้ตามหลักฐาน

- ออกแบบ Monte Carlo estimators พร้อม independent uncertainty units และ pilot accounting
- วัด accuracy/work/time/memory พร้อมระบุขอบเขต benchmark และกรณีล้มเหลว
- สร้าง self-financing hedge ledger และ paired experiments ที่ตรวจจาก raw paths ได้
- ส่งมอบ engine ที่เปลี่ยน config แล้วรันได้ พร้อมรายงานและหลักฐาน reproducibility

ควรแสดงรายงาน ตัวอย่างที่รันได้ และอธิบาย trade-off ด้วยตัวเอง
ไม่ควรอ้างว่าเป็นระบบเลือก options ทำกำไร หรือผ่านการรับรองพร้อมใช้เงินจริง

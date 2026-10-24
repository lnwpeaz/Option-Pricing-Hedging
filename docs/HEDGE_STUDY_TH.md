# ผลทดลอง hedging หลายเส้นทาง และสิ่งที่ใช้สรุปได้

ทำmilestone5แล้ว: ใช้ Monte Carloสร้างตลาดจำลอง10,000เส้นทาง
แล้วให้ทุกกลยุทธ์เจอตลาดชุดเดียวกัน เพื่อตอบว่าความถี่ ต้นทุนและvolatilityที่ใช้ผิด
เปลี่ยนความคลาดเคลื่อนของการreplicate callอย่างไร
นี่เป็นงาน short-call replication ไม่ใช่ผลตอบแทนของพอร์ตหุ้น/ETFของผู้ใช้

## รูปแบบการทดลองที่กำหนดก่อนรัน

S=K100,T1ปี,r5%,physical drift8%,true sigma20%,ไม่มีdividends
วันจำลองเป็นk/252ปีถึงexpiryexactly ไม่ใช่ปฏิทินตลาดที่รวมวันหยุด
ลองทุก1/5steps × ต้นทุน0/5/10bps × hedge sigma15/20/25% =18แบบ
เพิ่มunhedged baselineที่รับพรีเมียมตามแต่ละmodel sigmaอีก3แบบ
รวม21cases/210,000case-path rows ใช้path IDsเดียวกัน ไม่มีเลือกทิ้งกรณีผลไม่ดี

การสุ่มpathsคือMonte Carlo ส่วนdelta policyใช้สูตรanalyticเพื่อไม่เพิ่มnoiseในการตัดสินใจ
เก็บpaths.npy/times.npy,ผลทุกpath,metrics,paired contrasts และbootstrapstatistics

## ผลหลักเมื่อmodel sigmaถูกต้อง20%

หน่วยด้านล่างเป็นหน่วยราคาoptionจำลองหนึ่งหน่วย ไม่ใช่ผลตอบแทน%ของพอร์ต
RMSEคือขนาดความคลาดเคลื่อนรอบศูนย์ รวมทั้งbiasและdispersion; ต่ำกว่าหมายถึงreplicationแม่นกว่า

| นโยบาย | ต้นทุนbps | Mean P&L | RMSE | Bootstrap95%ช่วงของRMSE | Meanต้นทุนรวมดอกเบี้ยถึงT |
|---|---:|---:|---:|---|---:|
| ไม่hedge | 0 | −2.00329 | 16.99733 | [16.60466,17.40024] | 0 |
| ทุก1step | 0 | 0.00743 | 0.43122 | [0.42316,0.43868] | 0 |
| ทุก5steps | 0 | 0.01016 | 0.94984 | [0.93354,0.96803] | 0 |
| ทุก1step | 5 | −0.30994 | 0.54279 | [0.53366,0.55195] | 0.31736 |
| ทุก5steps | 5 | −0.17139 | 0.97187 | [0.95414,0.99101] | 0.18155 |
| ทุก1step | 10 | −0.62730 | 0.78820 | [0.77748,0.79877] | 0.63473 |
| ทุก5steps | 10 | −0.35293 | 1.02792 | [1.00924,1.04742] | 0.36310 |

ในกริดนี้ความถี่สูงลดerrorได้ แต่การซื้อขายมากขึ้นทำให้มีค่าใช้จ่ายมากขึ้น
ต้นทุน5bpsทำให้meanของdaily hedgeลดจาก0.00743เป็น−0.30994
ผลต่าง0.31736เท่ากับต้นทุนที่คิดดอกเบี้ยถึงexpiryแล้ว จึงเห็นtrade-offในบัญชีจริง
ค่าmeanใกล้ศูนย์เมื่อไม่มีต้นทุนไม่ได้เป็นกลยุทธ์สร้างกำไรจากตลาด

การเทียบทุก1ลบทุก5stepsที่sigma20%,cost5bps ให้RMSEdifference−0.42908
paired95%interval[−0.44634,−0.41135] โดยresamplepath IDsร่วมกัน
intervalนี้แสดงMonte Carlo sampling uncertaintyภายใต้โมเดล ไม่ใช่โอกาสที่
กลยุทธ์จะชนะในตลาดจริงหรือการรับรองว่าmodel assumptionsถูกต้อง

การดูโอกาสขาดทุนอย่างเดียวอาจทำให้เข้าใจผิด: ที่10bpsแบบทุก1stepมีP&Lติดลบ93.78%
แต่RMSEยังต่ำกว่าแบบทุก5stepsที่มีP&Lติดลบ65.82%
เพราะความถี่ของผลลบไม่ได้บอกขนาดของผลลบ ต้องดูmean/SD/RMSE/quantiles/ต้นทุนร่วมกัน

## ตั้งvolatilityผิด: แยกการรับพรีเมียมออกจากนโยบายhedge

การใช้model sigma15%,20%,25%ให้premiumเริ่มต้น8.59166,10.45058,12.33600
หากสมมติว่าขายได้ตามราคาทั้งสามนี้ การเทียบกำไรจะรวมผลจากการตั้งราคาด้วย
จึงเพิ่มcommon-premium P&Lโดยปรับ(C_ref−C_model)×exp(rT)ในทุกpath

ตัวอย่างทุก1step/cost5bps:

| Hedge sigma | Meanเมื่อรับpremiumของตัวเอง | Meanเมื่อรับpremiumเท่ากัน | RMSEเมื่อรับpremiumเท่ากัน |
|---|---:|---:|---:|
| 15% | −2.26904 | −0.31481 | 1.13146 |
| 20% | −0.30994 | −0.30994 | 0.54279 |
| 25% | +1.68117 | −0.30092 | 0.81168 |

sigma25%ไม่ได้พิสูจน์ว่าเราหากลยุทธ์ขายoptionที่ทำกำไรได้
มันสมมติให้รับพรีเมียมสูงกว่าราคาอ้างอิงไว้ตั้งแต่ต้น ยังไม่มีquoteตลาดว่าขายได้จริงเท่านั้น
เมื่อให้premiumเท่ากัน meanใกล้กัน แต่ความแม่นของhedgeต่างกัน
common-premiumเป็นcounterfactualเพื่อแยกสาเหตุ ไม่ใช่ราคาbidที่ส่งคำสั่งได้

มี42metric cellsและ102paired comparison rows รวมเปรียบเทียบcost/model sigma/
frequency/hedged-vs-unhedgedไว้ทั้งหมด ไม่เลือกwinnerโดยไม่รายงานส่วนที่เหลือ
ช่วงของmean/SD/RMSEและquantilesใช้bootstrap1,000ครั้งแบบpointwise percentile
probability-loss intervalใช้Wilson ไม่มีmultiple-testingหรือsimultaneous-coverage claim

## การกู้เงินระหว่างทางและการใช้เงินจริง

แบบsigma20%/ทุก1step/cost5bpsมียอดกู้เงินสดสูงสุดต่อpathเฉลี่ยประมาณ88.38674
แม้รับpremiumเริ่มต้นเพียง10.45058 เพราะซื้อหุ้นdeltaด้วยเงินกู้ที่บันทึกในบัญชี
ยอดกู้นี้ไม่ใช่broker margin,หลักประกัน หรือเงินทุนเริ่มต้นที่ปลอดภัย
โมเดลยอมให้กู้ได้ไม่จำกัดที่rเท่ากับฝากเงิน ยังไม่มีforced liquidationหรือslippage

funding fieldsที่ขึ้นต้นmodel_premiumอ้างถึงบัญชีpremiumเดิมเสมอ
แม้แสดงในcommon-reference metric row; ไม่ได้อ้างว่าเป็นยอดกู้ของบัญชีที่เปลี่ยนpremiumแล้ว
การทดลองนี้แยกterminal P&Lเพื่อศึกษาpolicy แต่ไม่ได้สร้างแผนทุนของพอร์ตจริง

ดู[ประเมินการใช้จริงและLong/Short options](PRACTICAL_USE_TH.md)
ซึ่งอธิบายว่าพอร์ตหุ้นและ ETF แบบ long-onlyเป็นlong-portfolio problemอีกแบบหนึ่ง
ยังไม่มีผลในงานนี้ที่วัดdrawdown reductionของพอร์ตนั้น

## มุมComputer Engineeringและการตรวจซ้ำ

ใช้vectorizationตามpathและวนตามเวลา เพื่อลดการสร้างPython ledger objectหลายล้านแถว
inputpathsเป็นO(NM);แกนdate loopใช้O(N)workspace แต่validationปัจจุบันมีboolean
arrayชั่วคราวO(NM)ด้วย จึงไม่อ้างว่าRAMรวมทั้งpipelineเป็นO(N)
ยังไม่ได้benchmarkpeak RSSหรือclaimspeedupจากtimingครั้งเดียว

เปรียบเทียบกับscalar ledgerบน16path IDsแรกของทุก21cases รวม336checks
maximum monetary differenceประมาณ7.96×10⁻¹³ ต่ำกว่าtolerance10⁻⁸
โดยไม่เปลี่ยนfinancial conventionsของแกนเดิม ตัวอย่างledgerใช้pathID0ตามที่กำหนด
ไม่ได้เลือกpathที่ผลสวย มีsource snapshotเพื่อกู้โค้ดและreplayในenvironmentที่บันทึก

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.runner
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/examples/milestone-5
```

ดู[ผลเต็ม](../reports/examples/milestone-5/RESULTS.md),
[กราฟrisk/cost](../reports/examples/milestone-5/risk_and_cost.png) และ
[กราฟvolatility/premium](../reports/examples/milestone-5/volatility_and_premium.png)
ขั้นโครงการเดิมถัดไปคือรายงานสรุปอังกฤษ ส่วนการใช้กับพอร์ตส่วนบุคคลต้องเพิ่ม
multi-asset long-portfolio risk layerและการตรวจข้อมูล/ต้นทุนตลาดจริงแยกต่างหาก

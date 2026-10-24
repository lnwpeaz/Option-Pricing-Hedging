# Roadmap และสิ่งที่ควรเรียน

Milestone 1 ทำแล้ว: Black-Scholes, Greeks, tests และตัวอย่างพร้อมกราฟ
Milestone 2A ทำแล้ว: CRR tree และ convergence demo
Milestone 2B ทำแล้ว: Monte Carlo เป็นแกนด้านการคำนวณ พร้อม 3 estimators และ CPU/memory benchmarks
Milestone 3 ทำแล้ว: เส้นทาง GBM, กริดเวลา, ไฟล์ paths และกราฟตรวจ physical/RN
Milestone 4 ทำแล้ว: self-financing ledger และตัวอย่างบัญชีหนึ่งเส้นทาง
Milestone5ทำแล้ว: paired hedge studyบน10,000paths พร้อมแยกpremium effects
Milestone6ทำแล้ว: รายงานอังกฤษ12หน้า ตัวอย่างสัญญาใหม่ และสคริปต์สาธิต ดู PROGRESS.md
เวลาประมาณ 8-12 สัปดาห์เมื่อมีพื้นฐาน probability/calculus และทำ 8-12 ชั่วโมงต่อสัปดาห์
ปรับเวลาเพิ่มได้ตามการทบทวนคณิตศาสตร์

| Milestone | งาน | หลักฐานว่าจบ |
|---|---|---|
| 1: Black-Scholes | validated inputs, call/put, delta/gamma/vega | ค่ามาตรฐานถูกต้อง, parity/boundary checks, กราฟและโน้ตอธิบาย |
| 2A: CRR pricing (ทำแล้ว) | CRR tree | hand-worked cases, probability validation และ convergence plots |
| 2B: Monte Carlo (ทำแล้ว) | plain/antithetic/control, batching, reproducible RNG และ benchmarks | repeated-seed RMSE/CI calibration, 4 กราฟ และผลเปรียบเทียบเวลา/หน่วยความจำ |
| 3: Simulation (ทำแล้ว) | exact GBM, explicit drift, irregular grid และ batched paths | deterministic/RNG tests, log/price moments, repeated RN discounted expectation และไฟล์ paths ทำซ้ำได้ |
| 4: Hedge accounting (ทำแล้ว) | short-call delta hedge และ transaction costs | ตรวจ ledger แบบคำนวณมือ; เงินสด ดอกเบี้ย payoff และต้นทุนตรงกัน |
| 5: Experiments (ทำแล้ว) | frequency/cost/misspecification grid และ unhedged baseline | เปรียบเทียบบน path เดียวกัน, CSV/manifest/กราฟ, uncertainty |
| 6: Research report (ทำแล้ว) | รายงานอังกฤษ12หน้าและสาธิตสั้น | ตัวอย่างสัญญาใหม่ ราคา/Greeks/MC/hedge และหลักฐานตรวจตัวเลข |

## งานแรก: Black-Scholes

1. อ่าน RESEARCH_SPEC.md และจดความหมาย S, K, r, sigma, T
2. ทบทวน payoff, present value, normal CDF และ expected value
3. เขียน tests/test_black_scholes.py สำหรับ baseline call/put และ parity ให้เห็นว่าล้มเหลวก่อน
4. ทำ OptionSpec และ price ให้ผ่าน รวม expiry/zero-volatility/input validation
5. ทำ Greeks และเทียบ finite differences ก่อนวาดกราฟ
6. อธิบายเป็นภาษาอังกฤษว่าทำไมราคา call เปลี่ยนเมื่อ spot/volatility เปลี่ยน

## แนวทางเรียนรู้

ก่อน coding แต่ละส่วน ให้เขียนสูตรและคำนวณตัวอย่างเล็กด้วยมือ
หลัง coding ให้เขียนว่าผลลัพธ์ตอบคำถามวิจัยอย่างไร และสมมติฐานใดทำให้ใช้กับตลาดจริงไม่ได้
เก็บ core formulas ใน src เท่านั้น; notebook เรียกใช้ core เพื่อทดลองและอธิบาย
ปัจจุบันมี implementation และ executable tests แล้ว รันด้วย python -m pytest -q

## นิยามว่าโปรเจกต์เวอร์ชันแรกเสร็จ

- numerical tests ผ่านใน environment ที่บันทึก dependency versions
- config เดิมและ seed เดิมให้ผล numerical เดิมภายใน tolerance ที่ประกาศ
- ledger และต้นทุนตรวจสอบได้ และรายงานไม่ซ่อน scenario ที่ผลไม่ดี
- รายงานแยก simulation จาก historical evidence อย่างชัดเจน
- ผู้เขียนอธิบาย risk-neutral pricing, discrete hedge error และ cost trade-off ได้ด้วยตัวเอง

## การเสริมคุณภาพขั้นที่ทำแล้ว — 21 ตุลาคม 2026

เพิ่ม independent payoff integration และกริดตรวจ 144 สถานการณ์พร้อม Monte Carlo
13,824 estimates เพื่อเห็นข้อจำกัดของ CI/rare payoffs นอกกรณีมาตรฐาน
การรันใหม่เก็บ source archive และมีเครื่องมือตรวจไฟล์/คำสั่ง replay แล้ว
ดู PROJECT_AUDIT_TH.md และ REPRODUCIBILITY.md สำหรับหลักฐานและข้อจำกัด
หลังเสริมคุณภาพแล้ว milestone4 ledger ทำเสร็จเมื่อ23ตุลาคม2026
milestone5และmilestone6รายงานทำเสร็จต่อแล้วในวันเดียวกัน
ดู HEDGE_STUDY_TH.md และ PRACTICAL_USE_TH.md

## ผลpaired studyพร้อมแล้ว

อ่าน HEDGE_STUDY_TH.mdสำหรับผลวัดจริง และ PRACTICAL_USE_TH.mdสำหรับขอบเขต
บริษัท/พอร์ตหุ้น/ETF/Long-Short options การนำไปใช้กับพอร์ตจริงยังไม่ถูกvalidate
รายงานอังกฤษเสร็จแล้วที่ output/pdf/option_pricing_hedging_research_report.pdf
ดู USE_CASE_TH.md และ DEMO_SCRIPT_TH.md เพื่อใช้ทดลองและสาธิต
ผู้ใช้เลือกคงโปรเจกต์นี้ด้านoption pricing/hedging/Monte Carlo engineering
ส่วนpersonal-portfolio risk layerเป็นอีกโครงการ ไม่รวมเข้ามาในเวอร์ชันนี้

ขั้นต่อยอดที่เสนอคือoption-quote diagnosticsและimplied volatility โดยต้องนิยาม
สัญญา/ข้อมูล/solver/เกณฑ์ตรวจให้ชัดก่อน ส่วนนี้ยังไม่ได้implement


## V2-A ที่ทำแล้ว — 24 ตุลาคม 2026

เพิ่ม Asian pricing, geometric control, scrambled Sobol และ Brownian bridge ครบ 5 วิธี
ทดลองครบ 2,880 estimates พร้อม time/allocation measurements และ custom pricing
อ่าน ASIAN_MONTE_CARLO_TH.md ซึ่งระบุ reference precision limitation ของทั้ง 6 สัญญา
ก่อนอ้าง accuracy ranking ต้องเพิ่ม reference convergence ด้วย protocol ใหม่
V2-B jump-risk hedging และ V2-C contract-aware quote/IV ยังไม่ได้ implement
งานนี้ไม่รวม stock selection หรือ personal-portfolio allocation

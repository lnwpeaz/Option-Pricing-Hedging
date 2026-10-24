# เริ่มเรียนจาก Milestone 1

## เปิดโปรเจกต์และรัน

จากโฟลเดอร์โปรเจกต์ เปิด environment ด้วย `source .venv/bin/activate`
ตามด้วย `export PYTHONPATH="$PWD/src"`
แล้วรัน `python -m pytest -q` และ `python -m option_hedging.experiments.pricing_demo`
แต่ละครั้งจะได้โฟลเดอร์ใหม่ใน reports/runs พร้อม CSV กราฟ และ manifest
หากย้ายโปรเจกต์หรือเปลี่ยนเครื่อง ให้สร้าง .venv ใหม่ตาม README เพราะ environment เดิมย้ายตามไม่ได้

## ตัวแปรที่ต้องอธิบายได้

| ตัวแปร | ความหมาย | ตัวอย่าง |
|---|---|---|
| S | ราคาสินทรัพย์อ้างอิงตอนนี้ | 100 |
| K | ราคาใช้สิทธิ | 100 |
| T | เวลาคงเหลือเป็นปี | 1 |
| r | ดอกเบี้ยทบต้นต่อเนื่องต่อปี | 0.05 |
| sigma | volatility รายปี | 0.20 |

European call ให้ payoff max(S_T-K, 0); put ให้ max(K-S_T, 0)
payoff ตอนหมดอายุต่างจาก premium ที่จ่ายวันนี้ และยังไม่ได้หักต้นทุนซื้อ option

## อ่านกราฟอย่างไร

- Option premium: เมื่อราคาหุ้นเพิ่ม call แพงขึ้นและ put ถูกลง ภายใต้ค่าอื่นคงเดิม
- Delta: ความไวของราคา option ต่อราคาหุ้น ใน baseline call delta ประมาณ 0.6368
  หมายถึงเมื่อหุ้นขึ้น 1 หน่วย ราคา call เปลี่ยนประมาณ 0.6368 หน่วยสำหรับการเปลี่ยนเล็ก ๆ
- Gamma: ความไวของ delta ต่อราคาหุ้น อธิบายว่าทำไม hedge เดิมต้องปรับเมื่อหุ้นเปลี่ยนราคา
- Vega: ความไวต่อ volatility โดยในกราฟแสดงต่อการเพิ่ม 1 percentage point
  baseline ประมาณ 0.3752 เช่น volatility เปลี่ยนจาก 20% เป็น 21% (การประมาณเชิงเส้น)
- Volatility sensitivity: option แพงขึ้นเมื่อ volatility เพิ่ม เพราะ payoff มีความโค้ง

## คำถามก่อนเรียน Monte Carlo

1. ทำไม call ราคา 10.4506 ทั้งที่ payoff ถ้าหมดอายุตอน S=100 จะเป็นศูนย์?
2. ทำไม call delta กับ put delta ต่างกัน 1 สำหรับสินทรัพย์ไม่มีเงินปันผล?
3. ทำไม vega ของ call กับ put จึงเท่ากันเมื่อใช้ตัวแปรชุดเดียวกัน?
4. ทำไมสูตรใช้ r ในการกำหนด risk-neutral distribution แทนผลตอบแทนหุ้นที่คาดหวังจริง?
5. การคำนวณ delta ถูกต้องหมายความว่า hedge แบบรายวันจะไม่มีความเสี่ยงแล้วหรือไม่?

## ทดลองด้วยตัวเอง

คัดลอก configs/baseline.toml เป็นไฟล์ใหม่ เปลี่ยน [option].spot จาก 100 เป็น 110
แล้วรัน demo ด้วย `--config configs/your-file.toml` เปรียบเทียบราคาและ delta
ต่อมาเปลี่ยน volatility จาก 0.20 เป็น 0.30 โดยคงค่าอื่นเดิม
ก่อนรันให้เขียนคำทำนายสั้น ๆ แล้วตรวจว่าผลสอดคล้องหรือไม่และเพราะอะไร

demo นี้อ่านเฉพาะ [option] การเปลี่ยน [simulation] หรือ [hedging] ยังไม่มีผล
ราคาเป็นค่าจากโมเดล ไม่มีการดึงราคาตลาดหรือทดสอบกำไรจากการ hedge ในขั้นนี้

## อ่านโค้ดตามลำดับ

1. src/option_hedging/contracts.py: นิยาม inputs และหน่วย พร้อม validation
2. src/option_hedging/pricing/black_scholes.py: สูตรราคาและ Greeks
3. tests/test_black_scholes.py และ tests/test_greeks.py: หลักฐานว่าคำนวณถูกต้อง
4. src/option_hedging/experiments/pricing_demo.py: นำสูตรไปสร้างตารางและกราฟ

กรณี T=0 หรือ sigma=0 ใช้ deterministic limits; Greeks ที่ kink ยก ValueError
ค่า option ที่เล็กมากอาจ underflow เป็นศูนย์ตามขีดจำกัด floating point
inputs ที่มีขนาดสุดขั้วจน intermediate computations overflow ยังไม่ใช่โดเมนที่รับรองสำหรับการวิจัย

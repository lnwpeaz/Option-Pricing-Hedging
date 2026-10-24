# Milestone 2A: CRR Binomial Pricing

ขั้นนี้เพิ่มอีกวิธีคำนวณราคา European option โดยแบ่งเวลาที่เหลือออกเป็น N ขั้น
แล้วให้ราคาสินทรัพย์ขึ้นหรือลงในแต่ละขั้น ก่อนย้อนกลับมาหาราคาวันนี้
demo นี้ไม่เรียก Monte Carlo และไม่มีราคาตลาดจริงหรือผลการ hedge
Monte Carlo lab ทำแยกแล้ว ดู MONTE_CARLO_TH.md

## วิธีรัน

จากโฟลเดอร์โปรเจกต์:

```sh
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m pytest -q
python -m option_hedging.experiments.convergence_demo
```

ผลแต่ละครั้งอยู่ในโฟลเดอร์ใหม่ใต้ reports/runs ประกอบด้วย CSV, summary.json,
กราฟ convergence.png, input_config.toml และ manifest ที่บันทึก source hashes/versions
ตัวอย่างที่รันแล้วอยู่ใน reports/examples/milestone-2a

## สูตรที่ใช้

สำหรับ dt=T/N และไม่มีเงินปันผล:

    u = exp(sigma * sqrt(dt))
    d = 1/u
    p = (exp(r*dt)-d)/(u-d)
    V_now = exp(-r*dt) * [p*V_up + (1-p)*V_down]

ที่ปลายต้นไม้คำนวณ payoff ของ call หรือ put แล้วใช้สูตร V_now ย้อนกลับทีละขั้น
ฟังก์ชันหลักอยู่ใน src/option_hedging/pricing/binomial.py
ใช้ backward induction จริง และไม่ได้เรียก Black-Scholes มาแทนคำตอบ

ความน่าจะเป็น p เป็น risk-neutral probability สำหรับการหาราคา ไม่ใช่การคาดการณ์
ว่าหุ้นจริงจะขึ้นด้วยโอกาสเท่านั้น หาก p อยู่นอก [0,1] กริดนี้ใช้ไม่ได้
โปรแกรมจะหยุดพร้อมแจ้งให้ปรับจำนวนขั้น โดยไม่ clip ค่า p
expiry และ sigma=0 ใช้ deterministic limits โดยไม่สร้าง p

## ตัวอย่างคำนวณมือ

กำหนด S=K=100, T=1, N=1, sigma=ln(2), r=ln(1.25)
ได้ u=2, d=0.5, p=0.5 และ discount factor=0.8

- หุ้นปลายทางเป็น 200 หรือ 50
- Call payoff เป็น 100 หรือ 0 จึงมีราคา 0.8*(0.5*100+0.5*0)=40
- Put payoff เป็น 0 หรือ 50 จึงมีราคา 0.8*(0.5*0+0.5*50)=20

นี่เป็นตัวอย่างที่ใช้ทดสอบต้นไม้โดยไม่พึ่งคำตอบของอีกโมเดลหนึ่ง

## อ่านผล convergence

ใน baseline S=K=100, T=1, r=5%, sigma=20%:

| วิธี | Call | Put |
|---|---:|---:|
| Black-Scholes | 10.4505835722 | 5.5735260223 |
| CRR 1001 ขั้น | ประมาณ 10.4523346903 | ประมาณ 5.5752771404 |

ความคลาดเคลื่อนประมาณ 0.0017511 หน่วยราคา option ต่อสัญญาจำลอง multiplier=1
เป็น discretization error ไม่ใช่ผลขาดทุนหรือกำไรจากการลงทุน
กริดมีจำนวนขั้นคู่และคี่ติดกันเพื่อให้เห็นการแกว่งรอบราคาอ้างอิง
การเพิ่มขั้นหนึ่งครั้งจึงไม่จำเป็นต้องทำให้ absolute error ลดทุกครั้ง

error ของ call/put อาจทับกันในกราฟเพราะ put-call parity ไม่ได้แปลว่าขาดข้อมูลฝั่งหนึ่ง
กราฟเวลาเป็นการวัดครั้งเดียวต่อกริด มี noise และ warm-up จึงยังไม่ใช่ benchmark
วิธี backward induction นี้ใช้เวลาระดับ O(N^2) และหน่วยความจำ O(N)

## ลองศึกษาเอง

1. คัดลอก configs/baseline.toml เปลี่ยน [option].spot จาก 100 เป็น 110 แล้วรันด้วย --config
2. ทดลองกริดคู่ทั้งหมดและคี่ทั้งหมดใน [convergence].steps; ต้องเรียงเพิ่มและไม่ซ้ำ
3. เปลี่ยน volatility แล้วดูว่าความคลาดเคลื่อนที่จำนวนขั้นเดิมเปลี่ยนอย่างไร
4. ลอง r=1.0, sigma=0.2 และกริด [1,2]; อธิบายว่าทำไม probability ใช้ไม่ได้
5. เขียนสรุปภาษาอังกฤษว่าเหตุใดความแม่นยำกับเวลาคำนวณต้องพิจารณาควบคู่กัน

convergence demo อ่านเฉพาะ [option] และ [convergence]; [pricing].tree_steps,
[simulation] และ [hedging] ยังไม่ถูกใช้ในการทดลองนี้
หากจำนวนขั้นหรือ volatility ทำให้ node prices เกิน floating-point range โปรแกรมยก ValueError
เช่นเดียวกับกรณี p ที่ควรอยู่ระหว่าง 0 กับ 1 แต่ถูกปัดเป็น endpoint เนื่องจากขีดจำกัดเชิงตัวเลข
และยังไม่มีการรับรอง input สุดขั้วทุกแบบ

อ่านต่อที่ MONTE_CARLO_TH.md: Monte Carlo pricing ที่รายงาน sampling error และ confidence interval
ต่างจาก CRR ที่เป็นวิธี deterministic สำหรับ inputs เดิม

# สคริปต์สาธิตประมาณ 5 นาที

ใช้รายงาน `output/pdf/option_pricing_hedging_research_report.pdf`
และผลที่มีอยู่แล้วใน `reports/examples/` ได้ทันที ไม่ต้องรอรันใหม่ระหว่างนำเสนอ

## นาที 0-1: โจทย์และขอบเขต

“ผมสร้างเครื่องมือวิจัยราคา European options และความเสี่ยงของการ delta hedge
คำถามหลักคือซื้อขายถี่แค่ไหนจึงลด replication error และต้องแลกกับต้นทุนเท่าไร
จุดที่เชื่อมกับ Computer Engineering คือทำ Monte Carlo ให้แม่นขึ้นต่อทรัพยากร
และตรวจผลได้ ไม่ใช่แค่สุ่มตัวเลขแล้วรายงานราคาหนึ่งค่า”

เปิดรายงานหน้า 1 และอธิบายว่า price accuracy, sampling uncertainty และ
ความถูกต้องของสมมติฐานตลาดเป็นคนละเรื่องกัน

## นาที 1-2: Monte Carlo เป็นแกน

เปิดหน้า 3-5: อธิบาย plain, antithetic และ control โดยใช้ตัวอย่างหนึ่งประโยคต่อวิธี
ชี้ว่าข้อมูลอิสระของ antithetic คือคู่ ส่วน control แยก pilot ออกจาก production

“ในสัญญามาตรฐาน call ที่ N=262,144 measured RMSE ลดจาก 0.03075 เหลือ 0.00975
ด้วย control variate และนับต้นทุน pilot แล้ว ผมยังวัด scalar/vector kernel ratio
ประมาณ 13 เท่าบนเครื่องนี้ แต่ไม่อ้างว่าเป็น end-to-end speedup”

เปิดหน้า 6: “เมื่อ payoff เกิดยาก อาจได้ SE=0 ทั้งที่ราคาจริงยังเป็นบวก
ผมเก็บผลเหล่านี้ไว้และแสดงข้อจำกัดของช่วงความเชื่อมั่น”

## นาที 2-3: Hedge accounting และผลที่มีข้อแลกเปลี่ยน

เปิดหน้า 2 แล้วหน้า 7-8:

“บัญชีรับ premium ซื้อหุ้นตาม delta ทบดอกเบี้ย จ่ายต้นทุนทุกครั้งและ settle
เมื่อหมดอายุ เทียบทุก policy บน path เดียวกันและ bootstrap path IDs ร่วมกัน
ที่ sigma=20%, cost=5 bps ปรับทุกขั้นมี RMSE 0.543 เทียบกับ 0.972 ทุกห้าขั้น
แต่เสียต้นทุนมากกว่า และการเพิ่ม premium ตาม model sigma ทำให้ดูเหมือนมีกำไรได้
จึงต้องแยก premium effect ออกจาก hedge-policy effect”

## นาที 3-4: เปลี่ยน input แล้วใช้งานได้

เปิดหน้า 10 และ `docs/USE_CASE_TH.md`:

“ผมทดลองสัญญาใหม่ S=120, K=125, อายุครึ่งปี ได้ call 7.33736 พร้อม Greeks
รัน MC อีก 1,728 estimates และ hedge อีก 63,000 path outcomes ผ่าน interfaces เดิม
เมื่อสร้างสถานการณ์ sigma=30% แต่รับ premium ที่ราคา sigma=25%
แม้ hedge ให้ตรงกับ scenario ก็ยังมี mean P&L ติดลบ
ระบบจึงช่วยตรวจว่า premium, hedge error และต้นทุนสัมพันธ์กันอย่างไร”

ระบุชัดว่าเป็นสัญญาสมมติ ไม่ใช่ market quote หรือผลกำไรจากการซื้อขายจริง

## นาที 4-5: ความน่าเชื่อถือและขั้นต่อยอด

เปิดหน้า 11-12 และโครงสร้างผลทดลอง:

“มี 390 tests รวมบัญชีแบบคำนวณมือและ scalar/vector checks
เก็บ config, raw paths, raw results, uncertainty, artifact hashes และ source snapshot
มีหลักฐาน replay numerical artifacts ใน environment ที่บันทึกไว้
ขั้นถัดไปที่ผมเสนอคือ contract-aware quote diagnostics และ implied volatility
โดยตรวจประเภทสัญญาและคุณภาพข้อมูลก่อน ไม่ได้ข้ามไปทำ portfolio optimizer”

## คำถามที่ควรตอบได้ก่อนใช้สมัครงาน

- ทำไม pricing ใช้ drift r แต่ hedge scenarios ใช้ mu?
- ทำไม antithetic 100,000 evaluations มีข้อมูลอิสระเพียง 50,000 คู่?
- ทำไม control ต้องแยก pilot และนับค่าใช้จ่ายนั้น?
- ทำไม SE=0 ไม่ได้หมายความว่าราคาแน่นอน?
- ทำไม RMSE, SD, probability of loss และ mean P&L ให้คำตอบต่างกัน?
- ทำไมต้องจับคู่ path IDs และตรึง premium ในการเปรียบเทียบบางเรื่อง?
- ผล 13 เท่าได้จาก benchmark ส่วนไหน และส่วนไหนยังไม่ได้วัด?
- ทำไมโมเดล European q=0 ยังแทน equity options สหรัฐฯ ไม่ครบ?

ถ้าตอบข้อใดไม่ได้ ให้ย้อนอ่านหน้าที่เกี่ยวข้องและอธิบายด้วยตัวอย่างเล็กก่อน
รายงานกับโค้ดเป็นหลักฐานการทำงาน ส่วนความเข้าใจต้องสาธิตได้ด้วยตัวเอง

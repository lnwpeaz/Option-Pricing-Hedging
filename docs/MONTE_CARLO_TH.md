# Monte Carlo Lab: เชื่อม Financial Engineering กับ Computer Engineering

Milestone 2B เป็นแกนด้านการคำนวณของโปรเจกต์: เราไม่ได้ถามแค่ว่าได้ราคาเท่าไร
แต่ถามว่าเชื่อคำตอบได้แค่ไหน ต้องใช้เวลาและหน่วยความจำเท่าไร และปรับอัลกอริทึมอย่างไร
จึงได้ความแม่นยำเพิ่มขึ้นต่อทรัพยากรที่ใช้

ชุดทดลองนี้ทำจริงแล้วทั้ง Plain MC, Antithetic Variates และ Stock Control Variates
ใช้หลาย seed หลายจำนวนตัวอย่าง หลายราคาใช้สิทธิ และเก็บผลทุกครั้ง
ผลการ hedge และเส้นทางราคาตลอดอายุสัญญาทำแล้ว ดู HEDGE_STUDY_TH.md
รายงานอังกฤษและตัวอย่างใช้งานเพิ่มเติมพร้อมแล้ว ดู USE_CASE_TH.md

## 1. เริ่มจากคำถาม ไม่ใช่การสุ่ม
ราคา European call คือค่าคาดหมายของ payoff ในอนาคตภายใต้ risk-neutral measure
แล้วคิดลดกลับมาเป็นเงินวันนี้:

    C = E_Q[exp(-rT) max(S_T - K, 0)]
    S_T = S0 exp((r - sigma²/2)T + sigma sqrt(T) Z),   Z ~ N(0,1)

Put เปลี่ยน payoff เป็น max(K-S_T,0) ใช้ drift r สำหรับ pricing
ส่วน mu=8% ที่กำหนดไว้สำหรับจำลองตลาดในอนาคตเป็นอีก measure หนึ่ง
อย่านำ mu มาแทน r เพื่อให้ราคา option สูงขึ้นตามผลตอบแทนที่คาดหวัง

เราใช้ Black-Scholes เป็นคำตอบอ้างอิงสำหรับตรวจ MC ในงานนี้
ตัว MC ไม่เรียกสูตรราคา Black-Scholes และไม่ได้ปรับคำตอบให้ตรงกับราคาอ้างอิง
ในโมเดลนี้ Black-Scholes เหมาะกว่าสำหรับคำนวณราคาโดยตรง แต่กรณีที่ไม่มีสูตรปิด
เช่น payoff ที่ซับซ้อนขึ้น แนวคิดและเครื่องมือของ MC จะมีประโยชน์มากขึ้น

## 2. ทำไมไม่จำลองราคาหุ้น 252 วันทุกครั้ง

European payoff ในงานนี้ขึ้นกับ S_T เท่านั้น และ GBM มีสูตรการเปลี่ยนผ่านที่แน่นอน
จึงสุ่มราคาปลายทางโดยตรงได้ ไม่มี time discretization error จากการแบ่งวัน
ส่วนที่เหลือคือ sampling error และ floating-point error

นี่เป็นการเลือกอัลกอริทึมให้ตรงกับข้อมูลที่จำเป็น:

| วิธี | งานต่อ N ตัวอย่าง | หน่วยความจำถ้าเก็บทุกค่า | เหมาะกับ |
|---|---|---|---|
| สร้าง path M ขั้น | O(NM) | O(NM) | hedge ที่ต้องใช้ราคาหลายเวลา |
| สุ่ม terminal โดยตรง | O(N) | O(N) ถ้าเก็บทั้งหมด | European payoff |
| สุ่ม terminal แบบแบ่ง batch | O(N) | O(B) เมื่อ batch size=B | European pricing จำนวนมาก |

ตัวอย่างเชิงขนาด: เมทริกซ์ float64 จำนวน 1,000,000 paths × 253 จุด
ใช้เฉพาะข้อมูลราคา 2,024,000,000 bytes ก่อนนับ array ชั่วคราว
การใช้ batch ไม่ต้องเก็บเมทริกซ์นี้ ผลด้านหน่วยความจำที่วัดจริงอยู่ใน engineering.png
เมื่อถึงงาน hedge เราต้องสร้าง path ตามเวลาจริง เพราะข้อมูลระหว่างทางจำเป็นแล้ว

## 3. Plain Monte Carlo และความหมายของ SE

ให้ Y_i เป็น discounted payoff ที่เป็นอิสระกัน:

    estimate = mean(Y)
    sample_variance = sum((Y_i - mean(Y))²) / (N-1)
    standard_error = sqrt(sample_variance) / sqrt(N)
    approximate_95_CI = estimate ± 1.959963984540054 * standard_error

Standard deviation ของ payoff บอกว่าผลลัพธ์แต่ละ path กระจายแค่ไหน
ส่วน standard error บอกความไม่แน่นอนของราคาเฉลี่ยที่ประมาณ
อย่าสลับสองค่านี้ และอย่าใช้ N แทน N-1 ใน sample variance

โดยทั่วไป SE ลดประมาณ 1/sqrt(N): ต้องเพิ่มงานประมาณ 4 เท่าเพื่อลด SE ครึ่งหนึ่ง
การเลือกอัลกอริทึมลด variance จึงอาจคุ้มกว่าการเพิ่มจำนวนตัวอย่างอย่างเดียว
อัตรานี้เป็นพฤติกรรมเชิงสถิติ ไม่ได้แปลว่าทุก seed ที่เพิ่ม N จะใกล้คำตอบขึ้นเสมอ

ช่วงความเชื่อมั่นที่ใช้เป็น normal approximation ไม่ใช่คำรับรองว่าทุกช่วงจะครอบคลุมราคา
ถ้า payoff เกิดยากมาก อาจสุ่มไม่เจอเลยแล้วได้ SE=0 ทั้งที่ราคาจริงยังเป็นบวก
รายงานจึงเก็บ zero_se_repeats และไม่แปลผลดังกล่าวว่าแม่นยำสมบูรณ์

## 4. Antithetic: ออกแบบการสุ่มให้ใช้ประโยชน์จากคู่ตรงข้าม

สำหรับ Z หนึ่งค่า ใช้ทั้ง Z และ -Z:

    A_i = (Y(Z_i) + Y(-Z_i)) / 2
    price = mean(A)
    SE = sample_std(A, ddof=1) / sqrt(number_of_pairs)

ตัวแปรทั้งสองมี marginal distribution ถูกต้องและเป็นคู่สัมพันธ์กัน
สำหรับ payoff แบบ monotone นี้มักช่วยลด variance แต่ระดับประโยชน์ขึ้นกับ payoff

**หน่วยข้อมูลอิสระคือ “คู่”** ถ้าตั้ง n_paths=100,000 เราคำนวณ payoff 100,000 ครั้ง
แต่มีข้อมูลอิสระ 50,000 คู่ จึงต้องใช้ค่าเฉลี่ยของคู่เพื่อคำนวณ SE
การเอา payoff 100,000 ค่าไปคิดเป็นข้อมูลอิสระจะทำให้ช่วงความเชื่อมั่นผิด

ฝั่ง CE: นี่เป็น algorithmic optimization เราเปลี่ยนความสัมพันธ์ของงานคำนวณ
เพื่อให้ข้อมูลที่ได้มีประโยชน์มากขึ้น ไม่ได้เปลี่ยน CPU หรือแค่เพิ่มจำนวนรอบ

## 5. Control Variates: ใช้สิ่งที่รู้แน่เพื่อลด noise

ให้ X=exp(-rT)S_T ภายใต้โมเดลไม่มีเงินปันผล เราทราบ E_Q[X]=S0
และ X มีความสัมพันธ์กับ payoff จึงสร้างตัวอย่างที่แก้ noise ได้:

    Y_adjusted = Y - beta * (X-S0)
    beta ≈ sample_cov(Y_pilot, X_pilot) / sample_var(X_pilot)

ถ้าชุดสุ่มมีราคาหุ้นเฉลี่ยสูงเกินค่าที่ควรเป็น เราปรับส่วนของ payoff ที่สัมพันธ์กับมัน
การแก้นี้ใช้ค่าคาดหมายของหุ้น ไม่ได้ใช้ราคาจริงของ option มาเฉลยให้ตัวเอง

เราแบ่งงานเป็นสองช่วง:

1. สุ่ม pilot 2,048 ตัวอย่างเพื่อหา beta
2. ตรึง beta แล้วสุ่ม production N ตัวอย่างใหม่ เพื่อประมาณราคาและ SE

Pilot และ production เป็นช่วงที่ไม่ซ้อนกันใน RNG stream ของ run นั้น
การตรึง beta จากชุดอิสระทำให้ใช้ sample SE ของ production ได้อย่างตรงไปตรงมา
จำนวน pilot ถูกนับเป็นงานเพิ่มในทั้งเวลาและ total_terminal_evaluations
ที่ N=1,024 pilot ใหญ่กว่า production; จึงไม่ควรสรุปว่าคุ้มจาก variance อย่างเดียว

ไม่ clip ราคา estimate หรือ CI ให้เข้าขอบเขตทฤษฎี เพราะจะเปลี่ยน estimator และซ่อนปัญหา
หาก pilot ไม่มี variance ที่สังเกตได้จริง โปรแกรมใช้ beta=0 แทนการหารด้วยศูนย์

## 6. ส่วนที่เป็น Computer Engineering โดยตรง

| หัวข้อ | สิ่งที่ลงมือทำ | หลักฐาน |
|---|---|---|
| Algorithm design | exact terminal sampling + variance reduction | RMSE และจำนวนงานต่อวิธี |
| Vectorization | ย้าย loop คำนวณ payoff ไปทำบน NumPy arrays | scalar/vector benchmark บน Z ชุดเดียวกัน |
| Memory management | แบ่ง batch และไม่เก็บตัวอย่างทั้งหมด | batch benchmark และ traced allocation |
| Numerical computing | สะสม central moments และปรับหน่วยด้วย S0 | tests ตรวจ SE เมื่อเปลี่ยนสเกลราคา |
| Reproducible systems | ระบุ RNG, seed IDs, config, dependencies และ hashes | manifest + exact input + seed_key |
| Experimental methodology | warm-up, หลายรอบ, สลับลำดับ และวัดงานเท่ากัน | raw benchmark CSV |

### Online reduction และ floating point

การสะสม sum(Y²)-sum(Y)²/N อาจเสียความแม่นยำเมื่อหักตัวเลขใหญ่ที่ใกล้กัน
เราใช้ batch-centered moments แล้ว merge ด้วยสูตร:

    delta = mean_b - mean_a
    mean = mean_a + delta * n_b/(n_a+n_b)
    M2 = M2_a + M2_b + delta² * n_a*n_b/(n_a+n_b)

ภายในคำนวณ payoff/stock ในหน่วย S0 ก่อน เพื่อหลีกเลี่ยงการยกกำลังสอง
ของจำนวนเงินที่เล็กหรือใหญ่มาก จากนั้นคืน mean และ SE ในหน่วยเงินจริง
Regression tests ตรวจ scale-equivalence ทั้ง 1e-170 และ 1e150 เท่าของ baseline
รวมถึง SE และ beta ไม่ใช่ตรวจราคาอย่างเดียว
หาก terminal values หรือ moments เกินโดเมนที่รองรับ จะหยุดพร้อมข้อผิดพลาด

### RNG stream design

ใช้ explicit PCG64 และ SeedSequence จาก:

    [1, kind_id, strike_id, N, repeat_id, method_id, root_seed]

แต่ละ cell/repeat จึงมี stream ของตัวเอง และทุก raw row มี seed_key สำหรับสร้างซ้ำ
นี่เป็นรากฐานสำหรับแยกงานไปหลาย worker ในอนาคต แต่รุ่นนี้ยังรันบน CPU แบบลำดับ
อย่าให้ทุก worker ใช้ seed เดียวกันแล้วนับผลซ้ำเป็นข้อมูลอิสระ

รับประกันการทำซ้ำในขอบเขต environment/config ที่บันทึกไว้
เราไม่อ้างว่าทุก NumPy build หรือทุกขนาด RNG call จะให้ bitstream เหมือนกัน
การเปลี่ยน batch อาจเปลี่ยนลำดับการบวกและ rounding จึงเทียบด้วย tolerance

## 7. อ่าน benchmark อย่างไรให้ไม่หลงตัวเลข

**Kernel-only:** สร้าง normals ไว้ก่อน ใช้ข้อมูลเดียวกันทั้ง scalar และ vectorized
จับเวลาเฉพาะการคำนวณค่าเฉลี่ย discounted payoff ทั้งคู่ไม่รวม RNG และ SE
ฝั่ง vectorized รวม validation และการสร้าง array; ฝั่ง scalar เป็น Python loop เพื่อการเรียนรู้
มี warm-up และสลับลำดับรัน เก็บทุก repetition แล้วสรุป median
ตัวเลขนี้ไม่ใช่ความเร็วที่เพิ่มขึ้นของโปรแกรมทั้งระบบ และไม่ใช่การชนะ compiled C/GPU

**Complete estimator:** รวมการสุ่ม payoff validation และ uncertainty
การเปรียบเทียบวิธีรวม pilot ด้วย ส่วนการทดสอบ batch ใช้ plain MC เหมือนกันทุกขนาด
เวลาที่รายงานไม่รวมการสร้าง Generator และการเขียนไฟล์/วาดกราฟ

**Memory:** วัด tracemalloc ในอีกรอบที่ไม่จับเวลา
เป็น peak allocation ที่ Python/NumPy tracing เห็น ไม่ใช่ process RSS
CPU cache, BLAS, scheduling และสภาพเครื่องทำให้ขนาด batch ที่เร็วที่สุดเปลี่ยนได้
ผลครั้งเดียวจึงใช้บอกพฤติกรรมบนเครื่องที่บันทึกไว้ ไม่ใช่เลือก batch ที่ดีที่สุดทุกระบบ

## 8. ชุดทดลองที่รันแล้ว

configs/monte_carlo.toml กำหนด:

- S=100, K=80/100/120, T=1 ปี, r=5%, sigma=20%; ทั้ง call และ put
- N=1,024 / 4,096 / 16,384 / 65,536 / 262,144
- 3 วิธี × 64 independent repeats ต่อ cell: รวม 5,760 ราคา และ 90 แถวสรุป
- Bootstrap 2,000 ครั้งสำหรับช่วง RMSE และ Wilson interval สำหรับ CI coverage
- Kernel 9 รอบ; batch sizes 512 / 4,096 / 32,768 / 262,144

อ่านผลตามลำดับนี้:

1. accuracy.png: RMSE ลดตาม N หรือไม่ และการกระจาย error แคบลงแค่ไหน
2. calibration.png: SE ที่รายงานสอดคล้องกับการกระจายจริงข้าม runs หรือไม่
3. robustness.png: ประโยชน์ของวิธีเปลี่ยนตาม strike และชนิด option อย่างไร
4. engineering.png: เวลาและ allocation เปลี่ยนตามวิธีและ batch อย่างไร
5. RESULTS.md: ตารางผล baseline และข้อจำกัด; metrics.csv เก็บทุก scenario

RMSE=sqrt(mean((estimate-reference)²)) รวมทั้ง bias และ variance
ช่วง bootstrap เป็นความไม่แน่นอนจากจำนวน repeats ที่มี ไม่ใช่หลักประกัน error ของ run ถัดไป
สัดส่วน coverage จาก 64 runs ก็ยังมีความไม่แน่นอน จึงแสดง Wilson interval กำกับ
Slope บนกราฟ log-log ที่ใกล้ -0.5 สนับสนุนพฤติกรรมตามทฤษฎี แต่ไม่ใช่บทพิสูจน์

การเทียบต้นทุนมีสามมุม: mse_gain ที่ N เท่ากัน, work_normalized_gain ที่นับ pilot,
และ time_efficiency_gain จาก median time × RMSE² ทั้งหมดเป็น empirical diagnostics
เราไม่ได้รันหยุดที่ wall-clock budget เท่ากัน จึงไม่อ้างว่าเป็นผลทดลอง equal-time โดยตรง

## 9. วิธีรันและใช้ API

จากโฟลเดอร์โปรเจกต์:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.monte_carlo_demo \
  --config configs/monte_carlo.toml --output-dir reports/runs/my-monte-carlo
```

โฟลเดอร์ผลลัพธ์ต้องยังไม่มีอยู่ โปรแกรมจะไม่เขียนทับผลเก่า
ไฟล์ config ของงานนี้แยกจาก baseline.toml เพื่อไม่ปนค่าที่ยังไม่ได้ใช้สำหรับ hedging
ทุกการรันเก็บ input_config.toml, effective_config.json, estimates.csv, metrics.csv,
kernel_benchmark.csv, batch_benchmark.csv, กราฟ 4 ภาพ, RESULTS.md และ manifest.json
Manifest เก็บ hashes ของ source/config/artifacts โดยไม่ hash ตัวมันเองแบบวนซ้ำ

```python
import numpy as np
from option_hedging.contracts import OptionSpec
from option_hedging.pricing.monte_carlo import price

spec = OptionSpec(100, 100, 1, .05, .2, "call")
result = price(spec, n_paths=100_000,
               rng=np.random.Generator(np.random.PCG64(43)),
               method="control", batch_size=32_768, pilot_paths=2_048)
print(result.price, result.standard_error, (result.ci_low, result.ci_high))
```

## 10. ใช้นำเสนอผลงานและต่อยอดอย่างไร

ประเด็นนำเสนอคือ “Statistically Reliable and Memory-Bounded Monte Carlo Option Pricing”
เล่าโจทย์การเงิน → ออกแบบ estimator → ตรวจความไม่แน่นอน → ปรับการประมวลผล → วัดผลจริง
แสดงให้เห็นว่าความเร็วที่ดีต้องคงความหมายทางสถิติ ไม่ใช่แค่ได้เลขเร็วขึ้น

งานต่อยอดที่มีเหตุผลหลัง baseline นี้ ได้แก่ randomized quasi-Monte Carlo,
CPU parallel streams และ GPU kernels โดยต้องรักษาหน่วยข้อมูลอิสระ/การรวมสถิติ
และวัดต้นทุนการส่งข้อมูลหรือสร้าง worker ด้วย ก่อนอ้าง speedup ทั้งระบบ
GBM หลายเวลาทำแล้วใน Milestone 3 ดู GBM_PATHS_TH.md;
ขั้นต่อไปคือ ledger เพื่อเชื่อมกลับไปคำถามหลักเรื่อง delta hedging
ไม่มีผลจำลองใดในขั้นนี้ใช้ยืนยันกำไรหรือประสิทธิภาพ hedge ในตลาดจริง

## แหล่งอ้างอิง

- [Martin Haugh, Columbia: Simulation Efficiency and Variance Reduction](https://www.columbia.edu/~mh2078/MonteCarlo/MCS_Var_Red_Basic.pdf)
  สำหรับหลักการ antithetic/control variates, pilot fitting และการพิจารณา variance ร่วมกับต้นทุน
- [NumPy: Parallel random number generation](https://numpy.org/doc/stable/reference/random/parallel.html)
  สำหรับการกำหนด stream ด้วย SeedSequence และชุด identifier
- [NumPy: RNG compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html)
  สำหรับขอบเขตการทำซ้ำเมื่อเปลี่ยน build, environment หรือรูปแบบ RNG calls

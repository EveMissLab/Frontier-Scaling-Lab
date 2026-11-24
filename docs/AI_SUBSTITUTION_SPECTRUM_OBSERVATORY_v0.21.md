# FSL v0.21｜AI 替代光譜觀測系統（ASSO）

**AI Substitution Spectrum Observatory**｜2026-11-24｜Canonical UTF-8 Markdown｜Apache-2.0 原創工程與文件。作者思想：Neo.K；研究協作：GPT-6.2／EveMissLab。狀態：可執行的結構審計與合成模型；尚無真實職業替代率實測或獨立認證。

## 1. 母框架與不變條款

本軌道直接承接 [ASTT 原稿索引](astt/README.md) 的 01、04、05、06；不改寫 GICCF v0.13 的 28 軸／224 指標／38 文明領域、不改寫 G1–G4/E1、不改寫 v0.17 兩道奇點門檻或 v0.20 製造品質標準。原始論文的條件命題、公開事件主張和有限模型均保留原有證據狀態；本版本未重新認證其中的外部科學主張。ASTT-02/03、07–09、10–12 與 EX01 的專門觀測將分期實作。

## 2. 觀測單位、事前契約與來源

一個 study 固定一個系統堆疊、一個註冊任務框、一種貨幣的最小記帳單位、一個相同長度且不重疊的基準／實施窗口。每個 contract 是指定領域、情境及基準的任務族，不是職業或人口本身。weight 是事前註冊的正整數採樣權重，而非事後挑選的成功樣本。需凍結 task set、驗收規格、原工作方式的 SHA-256、系統堆疊與事前註冊收據。不同組織、版本或貨幣建立不同 study，不能假裝同一比較框。域 ID 直接引用 GICCF，不複製或重新編號其 224 指標。

四種事件 trial / economics / deployment / augmentation 分別帶有來源、證據層、發生、首次公開及 FSL 記錄時間、工件 SHA-256 和（適用時）獨立評審聲稱。事件描述完整觀察窗的結果，不能在期末前出具。歷史修訂必須逐一 supersede 同契約同類型的前次記錄，不得覆寫舊資料。strict_known_at_time 不使用尚未公開或尚未錄入的事件；retrospective_reconstruction 允許後來錄入但當時已公開的材料。所有時戳需含時區；日期截止採 UTC 日末。註冊與外部獨立性仍是需核實的輸入聲稱。

## 3. 十二觀測軸

[機讀目錄](../data/asso_indicator_catalog_v0.21.json) 與 [JSON Schema](../data/asso_observation_schema_v0.21.json)。所有目錄值保留 null / not_measured。分子與分母在同一預定義契約中成立，輸出精確分數（numerator, denominator）而非任意百分比。分母為零或缺失時返回 null。

| ID | 觀測定義 |
|---|---|
| SUB-01 | 技術功能可替代性：accepted/attempts; weighted qualified contract share with unknown bounds |
| SUB-02 | 極高品質可達性：top_quality/attempts; not an occupation percentile |
| SUB-03 | 可靠性與錯誤：raw_error_trials/attempts; accepted_error_trials/delivered; delivery coverage |
| SUB-04 | 人類介入：human_core_minutes/attempts; declared cap |
| SUB-05 | 經濟可行性：baseline cost - full alternative cost + incremental value; operational gates |
| SUB-06 | 投資優先級：strict pair inversion within preregistered comparison group and cost basis |
| SUB-07 | 真實部署：active_units/eligible_units within declared cohort |
| SUB-08 | 原有任務轉移：transferred_prior_task_units/prior_human_task_units |
| SUB-09 | 人機增強：matched assisted per-human-hour output relative to baseline |
| SUB-10 | 人力需求變化：signed paid-hour and FTE compression; hires and exits separate |
| SUB-11 | 新任務與需求：new_task_families, new_paid_orders, accepted output change |
| SUB-12 | 實體環境與制度：safety, authorization, environment, blockers and physical receipt |

## 4. 可靠性、幻覺與合法可達性

attempts 是預定義任務試次（包含失敗）；delivered 是系統宣告交付之試次；accepted 是外部契約驗收為有效的試次；top_quality 是其中達更高門檻者。raw_error_trials 是原始候選流程被觀察到有重大錯誤的試次，accepted_error_trials 是錯誤穿越系統交付閘門而被外部稽核抓出的交付試次；它與 accepted 的有效驗收互斥。這些是任務試次層錯誤率，不是全球逐句幻覺率。人工實質核心工時除以試次；審核、供應商或客戶端補工是否納入需在契約明示。原始成功率、交付率、錯誤率、介入成本保持分開。

技術資格 = 有效驗收比例達標 AND 錯誤交付率不超標 AND 每試次核心人時不超標；已知失敗優先，其餘缺值保持 unknown。合法授權、安全及實體證據是另一組硬閘門。live_physical 必須有通過安全及物理收據；live_digital / live_physical 不能以 not_applicable 代替授權；安全通過聲稱和 SHA-256 並不等於真實安全認證。任何模擬或 sandbox 的能力結果不得擴張到 live_physical 之宣告。

## 5. 經濟可行性與替代優先級反轉

同一貨幣、時間窗與任務契約下，成本紅利為 B = baseline_cost_minor - alternative_cost_minor + incremental_value_minor。alternative_cost 應包含所有可歸屬 AI、設備、維護、人工審查、重試、風險／責任成本及已承諾資源，不以月費或 token 價格冒充全成本；baseline 要用可避免成本與一致固定需求比較，incremental_value 要扣除重複計算。不接受未聲稱完整成本的 B。實際帳與條件估計分列；只有實際成本且技術／安全／授權閘門已達標，才記錄 actual 經濟資格。B>0 是局部私人採用誘因，不是社會福利、已採用或已實現利潤。

SPI 配對只在事前同一 comparison_group、共同貨幣、投資者比較窗口及共同成本基礎內，且兩者操作閘門都通過時成立。異質任務是否在驗收尺度上可比較，須由研究契約另外證成，不能因欄位相同自動推定。若兩個任務的驗收比例差與 B 差乘積為負，即為反轉。平手、缺值、不合格配對另列。這不是職業消失機率；配對不獨立，本版不提供未經樣本設計之信賴區間。

## 6. 實際替代、增強、就業與物理部署

deployment 僅在共同抽樣母體記錄 active/eligible；prior_human_task_units 是基準期原有人類任務量，transferred_prior_task_units 必須是可對回基準任務束的轉移量，不能使用新增 AI 任務充當原人力替代。工時／FTE 的 signed compression 允許負值（擴張）。hire/exit/involuntary exit 是流量，不從淨人數推算裁員。產出量、新任務族及付費訂單分開。augmentation 只以同契約的人類與人機混合工作者合格成果／人時比較，不用純 AI 輸出冒充人類增強。所有數值均允許 null；原有需求、合格品、基準窗口、設備利用率及外包轉移等需另經來源驗證。

物理安全、授權、維護、在地化環境和 FSL v0.20 製造檢測可作真實場景的附加證據。不能把軟體成功或純模擬當成物理部署，亦不由設備設計推出產業量產。

## 7. 未知界與資料隔離

每個領域只報告其預註冊抽樣框內的技術資格與實際經濟資格。known_share = passed / (passed + failed)；coverage = known / frame；lower = passed / frame；upper = (passed + unknown) / frame。它們是缺值敏感性界，不是統計信賴區間，更不是全國職業替代率。沒有跨領域總分。經濟成本估計獨立，不進入實際經濟資格的成功比例。provider_claim、provider_demo、unobserved 保留收據但不計算結果；repeatable_test 以上需要工件哈希，而獨立層需要評審參照，這仍只是待核實聲稱。synthetic_fixture 僅可存在於 synthetic study，禁止攜帶外部評審或來源 URL，所有計算輸出另放 synthetic_scenario。observational 資料結構合法不代表內容真實。

## 8. 使用及重播

```bash
python -m fsl_substitution.cli catalog
python -m fsl_substitution.cli audit --file tests/fixtures/asso_synthetic_v0.21.json --as-of 2026-11-24T10:30:00Z
python -m fsl_substitution.cli audit --file tests/fixtures/asso_synthetic_v0.21.json --as-of 2026-11-24T11:30:00Z --mode retrospective_reconstruction
python -m unittest discover -s tests -p test_asso_v021.py -v
python -m unittest discover -s tests -v
```

合成案例包含數學／餐飲的純虛構成本、驗收率及部署，不得作為兩種職業真實能力、價格、風險或用工證據。它示範嚴格配對的排序反轉、同時任務轉移與 FTE 不變、修訂歷史和未知界。觀測資料的因果識別、樣本代表性、外部收據核驗與持久性資料庫需要後續實驗；本版是只讀事件審計，不是實時職業預報服務。

## 9. 後續獨立軌道（規劃，未實作）

- v0.22 KIF：ASTT-02/03，知識產生、解讀、跨域橋接與專業再分層。
- v0.23 HCAO：ASTT-07/08/09，異質時代拓撲、跨域耦合與吸收。
- v0.24 RSDO：ASTT-10/11/12，殘餘稀缺、受益權與制度。
- v0.25 RRAO：ASTT-EX01，作者依賴消融及持續新研究留出試驗。

# Frontier-Scaling-Lab v0.18：數據中心法律、選後治理與有效 AI 產能

**Legal and Regulatory Feasibility Observatory for AI Infrastructure**  
**2026-11-08（Asia/Taipei）｜UTF-8 Markdown canonical source｜原創研究協定／非個案法律意見**  
**狀態：7 項有日期的初步法律／政策紀錄、12 項研究主軸、60 項待測指標；沒有任何法規—算力供應的因果效果認證。**

## 一、為何法律現在必須進入 AI 基礎設施研究？

本研究承接 2026-11-06《美國 AI 數據中心：2026 期中選舉後的跨黨派反彈、擴建規模與水電聲環境衝突》原札記，也接續 FSL v0.13–v0.17 的文明能力、反事實、網路建設和系統性 AI 奇點研究。

2026 年 11 月 3 日，美國期中選舉後，美聯社報導民主黨取得參眾兩院控制權，但這是**政治事件，不是數據中心法令自動生效的法律事件**。Ballotpedia 的 2026-11-04 彙總中，47 項地方數據中心相關措施已有決定，其中 46 項結果傾向增加限制；其 11 月 6 日另篇文章只計 11 月 3 日當天，為 41 項中 40 項。兩者觀測範圍不同，而且同時涵蓋具拘束力措施、非拘束性諮詢及反對支持開發的提案，**不能全部當作已生效禁建**。

- AP： https://apnews.com/article/midterm-election-house-senate-democrats-republicans-trump-f126e12e05b579a327b98481c0ae2226
- Ballotpedia 總覽： https://ballotpedia.org/2026_ballot_measure_election_results
- Ballotpedia 11 月 6 日分母說明： https://news.ballotpedia.org/2026/11/06/voters-favored-limiting-data-center-development-in-40-of-41-local-ballot-measures-on-nov-3/

研究的主問題不是「選後哪個政黨限制 AI」，而是：

> 已有資金、晶片、工程與電力計畫的數據中心，經過哪幾個法律、行政、司法及社會參與程序，才能轉變成合法、實際上線、可維護的 AI 支撐產能？又有哪些法律機制能促成、附條件促成、延緩、轉移或禁止這一轉變？

政治表態、法案提出、議會通過、簽署、生效、正式執行、法院暫緩、現場許可、真正接電、商用算力與社會效果是**不同事件及不同時間軸**。

## 二、12 個研究軸與 60 項研究指標

機讀目錄位於 [data/ai_datacenter_legal_governance_2026-11-08_v0.18.json](../data/ai_datacenter_legal_governance_2026-11-08_v0.18.json)。

| 軸代號 | 研究範圍 | 必須獨立測的內容 |
|---|---|---|
| JUR | 法源及管轄 | 聯邦、州、市、歐盟、中央與實際適用主體 |
| STA | 法規生命週期 | 提案、簽署、生效、日落、廢止及拘束力 |
| ZON | 用地建築許可 | 分區、用途變更、審查、既有權利 |
| ELC | 電力及接入費率 | 併網容量、費率、成本分攤、擔保與接電 |
| WAT | 取水與冷卻 | 取水權、流域、排放、限水及回收水 |
| AIR | 空污與備援機組 | 柴油／燃氣發電排放許可、實際運轉條件 |
| ENV | 社區與環境審查 | 噪音、土地、環境評估、居民參與 |
| TAX | 稅制與優惠 | 用電稅、優惠、開發商擔保、閒置成本 |
| JUD | 司法救濟 | 禁制令、上訴、先例效力、優位法衝突 |
| DAT | 資訊申報及治理 | 能源、水、數據、網路及安全透明 |
| LAB | 勞動／工地安全 | 消防、施工職安、雇用及緊急應對 |
| CMP | 比較法與動態效果 | 美國、中國、歐盟及跨境投資遷移 |

每軸 5 項，共 60 項；只是定義，不是已驗收案例數、法律強弱分數或合規審查結論。

## 三、第一批法律、行政與政策證據：美國、中國、歐盟

| 案例（來源日期） | 法律或政策狀態 | 可確認的範圍與邊界 |
|---|---|---|
| 美國 FERC（2026-06-18） | 六個區域電網業者的 Section 206 大型負載費率／併網「說明理由或修訂」命令 | 監管程序要求，不是對全國數據中心的禁止建設 |
| 維吉尼亞州 HB1191（2026-06-30） | 州長公告已簽署 | 對大型用電戶投資新電力基礎設施及一般費率用戶保護有關；個別條款生效日未在此獨立核對 |
| 賓州 SB1359（NCSL 2026-09-15） | NCSL 當時標示 Introduced | 是州層級暫緩提案，不當作 11 月已實施 |
| Piqua, Ohio（2026-11-03） | >25 MW 數據中心市憲章限制修正案的非正式投票結果通過 | 尚需認證，是否適用已有工程及司法審查不明 |
| Bloomington, Illinois（2026-11-03） | 大型數據中心暫緩措施的諮詢性公投非正式結果通過 | 非拘束性「建議」，不等於市政府已訂出禁建法律 |
| 歐盟 (EU) 2024/1364（2024-05-17） | EUR-Lex 登記為已生效的歐盟授權規則 | 對裝設 IT 功率至少 500 kW 的數據中心設能源、水與永續等申報指標；不等於全面禁建 |
| 中國官方綠色數據中心行動方案（2024-07-24） | 公告政策目標及實施方向 | 包含 PUE、綠色能源、能效與用水方向，不能預設每項均為各地直接強制的禁建規則 |

可核對來源：
- FERC： https://www.ferc.gov/news-events/news/ferc-launches-aggressive-targeted-action-speed-large-load-integration
- 維吉尼亞州政府： https://www.governor.virginia.gov/newsroom/news-releases/2026/june-releases/name-1120477-en.html
- NCSL（2026-09-15）： https://www.ncsl.org/fiscal/which-states-are-banning-data-centers
- Piqua ballot： https://ballotpedia.org/Piqua,_Ohio,_Prohibit_Data_Center_Construction_Initiative_(November_2026)
- Bloomington ballot： https://ballotpedia.org/Bloomington,_Illinois,_Large-Scale_Data_Center_Moratorium_Advisory_Measure_(November_2026)
- EU： https://eur-lex.europa.eu/eli/reg_del/2024/1364/oj
- 中國國務院官網： https://english.www.gov.cn/news/202407/24/content_WS66a0b167c6d0868f4e8e96ba.html

每筆資料記錄**來源發布日、FSL 首次取得日、法規狀態和未知的生效日**。發言或投票有記錄，不代表其法律最終效力、個別廠址合法性或對電價的實際影響已證明。尤其 Piqua、Bloomington 的選務認證狀態與 11 月 8 日的法效尚需持續核對。

## 四、三條比較路徑：批准、附條件批准、暫緩禁止

延續舊札記的命題 D，以**相同規模與相近物理條件的可比案場**，研究：

- **無條件批准**：建設進度、電價、地方工作、環境成本、未來閒置資產及成本轉嫁；不是假定建設一定完成；
- **有條件批准**：對電力成本、用水、噪音、保證金、公開申報及可中斷負載附條件，觀測負擔、進度、效益與可執行性；
- **暫緩或禁止**：辨認適用對象、期限、例外、既有權利、司法效力及投資是否轉移，而不是假定會直接降低全球 AI 需求。

三條路徑皆須追蹤**實際**核准、動工、接電、裝機、運轉、工時、住戶費率、流域水量、排放及社會收益。選擇哪條政策屬公民與制度決策，不由 FSL 替某政黨選定最好路徑。

## 五、法律如何進入 FSL 與真 AI 奇點？

可按以下不同門檻分層：

\`\`\`text
市場需求與投資提案
    -> 土地、用水、環境、工程及電網許可
    -> 施工與可供應電力
    -> 已安裝且可運轉的硬體與網路
    -> 真實有效的 AI 支撐能力
    -> AI 可歸因的產能再生（須另一套證據）
    -> 跨週期再生及文明正和（仍須另行驗證）
\`\`\`

法律是物理建設能否實際發生的**制度可行性條件**，不是 SAS-01 原始八維狀態向量中的任意新數字。法律允許建設不代表奇點成立，法律禁止某地建設也不意味 AI 整體技術前沿停止。

- **接 FSL v0.1–v0.5：** 規劃的 MW、土地、園區數不能直接算成已上線有效算力；
- **接 v0.16：** 網路、衛星、海纜和數據中心建設的法定許可與跨境服務權要分開；
- **接 v0.17／SAS-01：** 法規影響可能限制或促成有效支撐能力，但再生係數、AI 因果歸因、物理閉環及文明正和仍需各自驗證；
- **接 EveClimateDynamics：** 法律決定可否建設、用水及排放如何約束，氣象與能量模型仍以獨立物理量測／數值驗證為準；法律事件不能改寫氣候實證。

## 六、維持動態資料庫與防止後見之明

本研究不把「民主黨勝選」當作 2026 年 6 月已簽署的法規的成因；不把 11 月的分析倒寫成 9 月已掌握的法律資訊。所有新發生的州議會進展、法規生效、選務認證、法庭裁決或許可決定，都必須作為**新事件**追加並連接先前事件，不得覆寫當年法源原文及狀態。

稽核支援：
- **strict_known_at_time**：只有該觀察截止日以前，來源已公開且 FSL 已登錄者；
- **retrospective_reconstruction**：允許在後來取得以前已公開的原始材料，但明示後來取得，不偽裝成當年的預測。

缺乏精確生效日、法律條文或行政許可資料時使用 \`null\`／\`unknown\`，不使用 0 或「已禁止」。任何法律對投資、GPU 產能或國民電價的影響，都需另外建立預註冊的反事實與對照組，不從法規種類直接推論。

### 程式與資料

\`\`\`bash
python -m fsl_legal.cli validate
python -m fsl_legal.cli replay --as-of 2026-11-07 --mode strict_known_at_time
python -m fsl_legal.cli replay --as-of 2026-11-07 --mode retrospective_reconstruction
python -m fsl_legal.cli replay --as-of 2026-11-08 --mode strict_known_at_time
python -m unittest discover -s tests -q
\`\`\`

**結論：AI 的工程可行域與法律可行域並不相等。真正值得持續追蹤的，是技術、資源、權限、居民成本與制度調整，如何在具體時間和地點共同決定可實際部署的 AI 文明支撐能力。**

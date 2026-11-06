# Frontier Scaling Lab v0.9 — 2024–2026 前沿 AI 歷史、同期比較與 AMRAL／FELRA 研究證據橋接

**研究日期：2026-11-07（Asia/Taipei, UTC+08:00）**  
**Canonical source：UTF-8 Markdown；唯一數學分隔符為 $...$、$$...$$**  
**研究狀態：49 筆官方發布／定價事件和分析程式；尚無獨立驗證的跨模型 24–48 小時 Agent 完成率實證。**  
**原創文件與程式：Apache-2.0；第三方與私人來源不因此改變授權。**

## 0. 研究問題

先前研究已建立功能性 AI 目標：G1 是跨數天至數月從意圖到結果的持續自主能力；G2 是在 G1 前提下適時變更、維持、澄清或升級策略；G3 是完整且頂級的遊戲／App 成品；G4 是高品質個人風格與獨特 AI 原生藝術；E1 是獨立的具身多任務適應。

v0.9 回答三個資料問題：（1）2024、2025、2026 各時間點有哪些**有官方日期與來源**的模型、工具、付費路徑？（2）同期前沿與非前沿 AI 是否具有同任務、同品質、同 runtime 的可比較紀錄？（3）AMRAL 真實數學研究歷程和 FELRA 獨立驗證，如何安全接入以後的成本與自主性研究？

模型推出日期、排行榜評分、API Token 報價與真正完成數月任務並非等價證據。歷史資料必須同時保存發布日、資料取得日、任務發生的實際時間與服務當時的可用條件。

## 1. 真實官方發布事件資料

來源：data/official_ai_history_2024_2026_v0.9.json。

第一階段總計 **49 筆模型／工具／價格／退役事件、38 筆具日期的官方來源項目、五家供應商、三個曆年（2024–2026）**。38 是登錄來源項目，不代表 38 個完全不同網站：同一官方變更紀錄可能有多個日期小節。49 也不是 49 個獨立模型。

五家供應商為 OpenAI、Anthropic、Google、xAI 和 DeepSeek。

| 日期 | 供應商 | 具時間版本的事件 | 重要限制 |
|---|---|---|---|
| 2024-02-15 | Google | Gemini 1.5 長上下文有限預覽 | 長 context 不等於多日自主 |
| 2024-05-13 | OpenAI | GPT-4o 發表並分方案推出 | Free／Plus 額度不同 |
| 2024-06-21 | Anthropic | Claude 3.5 Sonnet 推出；當時每百萬輸入／輸出 Token 報價 $3／$15 | 不能將點價自動延長至 2026 |
| 2024-08-13 | xAI | Grok-2 Beta 於 X 上線 | API 當時屬後續計畫 |
| 2024-09-12 | OpenAI | o1-preview 推出 | API／ChatGPT 需按當時存取限制處理 |
| 2024-12-11 | Google | Gemini 2.0 Flash Experimental 與 Deep Research | 模型與 Agent 工具渠道不同 |
| 2024-12-26 | DeepSeek | V3 上線 deepseek-chat API 別名 | 別名之後可能變動 |
| 2025-01-20 | DeepSeek | R1 推出 | 開放權重不等於當時自帶長程 Agent |
| 2025-02-19 | xAI | Grok 3、DeepSearch | API 另有推出時間 |
| 2025-02-24 | Anthropic | Claude 3.7 Sonnet 與 Claude Code 預覽 | 工具預覽不同於完全可用 |
| 2025-03-25 | Google | Gemini 2.5 Pro Experimental | 該日不應捏造未宣布的費率 |
| 2025-05-22 | Anthropic | Claude Opus 4、Sonnet 4 | 公司自己發布的基準不是 G1 實證 |
| 2025-07-09 | xAI | Grok 4 | 各方案額度與工具有別 |
| 2025-08-07 | OpenAI | GPT-5 | 多路由產品不等於一個凍結權重 |
| 2025-11-18 | Google | Gemini 3 | 使用渠道分開核對 |
| 2025-11-24 | Anthropic | Claude Opus 4.5，發布日 $5／$25 API 報價 | 僅可確認當時報價點 |
| 2026-02-05 | Anthropic | Claude Opus 4.6 | 發表宣稱不是 48 小時完成實測 |
| 2026-02-17 | Anthropic | Claude Sonnet 4.6 | Free／Pro 和 API 的權限不同 |
| 2026-02-19 | Google | Gemini 3.1 Pro | 試驗與一般正式供應不同 |
| 2026-03-05 | OpenAI | GPT-5.4 | 不可由模型名字推出訂閱容量 |
| 2026-04-24 | DeepSeek | V4 Pro／Flash API | 追蹤後續 API 別名更替 |
| 2026-09-03 | OpenAI | GPT-6 Astra | 有發布及安全／存取範圍 |
| 2026-09-10 | DeepSeek | V4.1 Flash | 官方自評需控制環境後才能比較 |
| 2026-09-22 | OpenAI | GPT-6 Sol／Luna | Work／Codex 與 Chat 是不同產品路線 |
| 2026-09-29 | OpenAI | GPT-6.1 Sol、Pro 500 | 訂閱價格不等於 API Token 成本 |
| 2026-10-17 | DeepSeek | Search & Fetch API | 工具出現不代表 G1 完成 |
| 2026-10-23 | OpenAI | GPT-4o 2024-05-13 特定 API 快照停用 | 不是整個 GPT-4o 家族消失 |
| 2026-10-26 | OpenAI | GPT-6.1 Terra；當日標準 API $1／$0.05 快取／$5 每百萬 Token | 當日點價，不是永久固定的通用價格 |

上述表只是重要節點，完整 49 筆在 JSON 原始事件表。

官方來源例：
- https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/
- https://openai.com/index/introducing-openai-o1-preview/
- https://openai.com/index/introducing-gpt-5/
- https://openai.com/index/introducing-gpt-5-4/
- https://openai.com/index/safety-overview-gpt-6-astra/
- https://help.openai.com/en/articles/9624314-model-release-notes
- https://www.anthropic.com/news/claude-3-5-sonnet
- https://www.anthropic.com/news/claude-3-7-sonnet
- https://www.anthropic.com/news/claude-opus-4-5
- https://www.anthropic.com/news/claude-opus-4-6
- https://blog.google/innovation-and-ai/products/google-gemini-next-generation-model-february-2024/
- https://blog.google/innovation-and-ai/models-and-research/google-deepmind/google-gemini-ai-update-december-2024/
- https://blog.google/products-and-platforms/products/gemini/gemini-3/
- https://x.ai/news/grok-2
- https://x.ai/news/grok-4
- https://api-docs.deepseek.com/updates/

供應商原始網頁有可能被後續修改，FSL 只保證本研究在 2026-11-07 取得並保存了這份來源指向與摘要，**不宣稱這些網頁擁有第三方不可變時間戳**。

## 2. 時間：嚴格歷史已知／事後重建

對每個事件記錄 $e_i$（生效日）、$p_i$（發布日）、$c_i$（首次由 FSL 取得來源的日期）。真正已在舊時間發出的研究預測，只能利用當時已發生、公開且已取得的來源：

$$
e_i\le t,\qquad p_i\le t,\qquad c_i\le t.
$$

若本研究在 2026 年才收集 2024 年文章，對 2024 的原始預測而言不算當時已知，但仍可在**清楚標示為事後重建的研究**中提供歷史證據。

價格、模型身份與可用性必須區分：
- API 發布當日價格只是一個 point quote。沒有下一張有日期的價目表，不可假定一直有效。
- 產品 API 別名會指向不同時間的版本；不得用別名替代精確模型快照。
- 模型推出不代表當時 Free／Plus／Pro 都能使用相同工具與算力；也不能把它推定到未來。
- 聲稱「當時是前沿模型」必須有事前定義的比較範圍及同時期依據，不能只拿 2026 年的排名倒推。

## 3. 同期矩陣與現有真實 Benchmark 的再利用

fsl_history/catalog.py 可以對 2024-12-31、2025-12-31、2026-11-07 等日期分別列出五家供應商此前已公開的版本。輸出是**歷史公告覆蓋率**，而非可重跑模型清單或能力排名。

所有沒有證據的欄位保持 null：例如截止日的可呼叫權限、訂閱剩餘額度、實際 24–48 小時 G1 完成件數、同品質任務的成功率及每件驗收成本。

fsl_history/metrics_bridge.py 可唯讀匯入 FSL v0.3/v0.4 已有 Arena／Hugging Face 來源觀測 SQLite，依模型外部身分、方法、來源及發布／取得日期分層。評分方法或版本不同時不自行轉成同一個「智能」數字，也不從總評分計算有效任務購買力。

v0.8.1／v0.8.2 的費用模組在任務真正經過同品質獨立驗收後，才有資格計算每項完成成果的成本；否則必須保留待判定或反事實情境。

## 4. AMRAL／FELRA 私有研究接入

FELRA 的 PPV 文件說明，單次 run 的典型產物包含：
- ppv/receipts.json
- ppv/status.json
- ppv/ledger.jsonl
- ppv/ppv_report.md

「status.json 寫有 VERIFIED」不是 FSL 能引用的證明。FELRA ppv-verify 需要實際重演收據、雜湊鏈、核心運算及特定 SMT／Lean 義務；不同證據類型的保證強度不同。

因此新增 fsl_history/research_bridge.py：

1. 只讀指定的本地／私人研究工作區。要求 epoch 身分、來源 Git Commit 全 SHA、Runtime manifest、任務契約 hash，以及研究開始、完成、證據收集時刻。
2. 選定檔案後計算實際 SHA-256；禁止路徑逃脫、symbolic link、檔案超界及申報 hash 不符。
3. 說明「原始資料位元組確認」與「獨立運行 FELRA 驗證」的差異，並且不會自行執行私有研究程式或將原始研究複製到 FSL。
4. 若使用者明確啟用公開匯總，可用私下提供的 HMAC 金鑰產生假名化 epoch 與來源修訂。輸出只包含材料種類數、來源完整性、已申報研究時長與未認證狀態；不包含私人檔名、分支名、數學原稿或原始檔案 SHA。
5. 即使完整材料都存在，也不會把歷史 Opus 18 小時研究直接認定為已獨立驗證的跨日能力。

這是私有研究接入**程式與契約**，不是宣稱已經在用戶的長程 Agent 機器上取得完整執行日誌或完成數學獨立驗證。

## 5. 可重現執行（Python 3.11+）

~~~bash
python -m unittest discover -s tests -v

python -m fsl_history.cli validate

python -m fsl_history.cli timeline \
  --as-of 2024-12-31 --mode strict_known_at_time

python -m fsl_history.cli timeline \
  --as-of 2024-12-31 --mode retrospective

python -m fsl_history.cli matrix \
  --month-ends '2024-12-31;2025-12-31;2026-11-07'

python -m fsl_history.cli metrics \
  --db /path/to/existing_fsl_evidence.sqlite \
  --model EXACT_SOURCE_MODEL_ID --as-of 2026-11-07

# 在自己的私人工作區先計算真實檔案雜湊，不需要手動填表
python -m fsl_history.manifest_cli \
  --root /path/to/private/research \
  --output /path/to/private/epoch_manifest.json \
  --epoch-id ACTUAL_EPOCH_ID --research-line ACTUAL_RESEARCH_LINE \
  --source-branch ACTUAL_GIT_BRANCH \
  --source-commit-sha ACTUAL_FULL_GIT_SHA \
  --model-provider anthropic --model-revision ACTUAL_MODEL_REVISION \
  --started-at 2026-11-05T08:00:00+08:00 \
  --runtime-manifest-sha256 ACTUAL_RUNTIME_SHA256 \
  --task-contract-sha256 ACTUAL_TASK_SHA256 \
  --material felra_ppv_receipts=ppv/receipts.json \
  --material felra_ppv_status=ppv/status.json \
  --material felra_ppv_ledger=ppv/ledger.jsonl

# 回頭驗證私有檔案是否真的與指定 SHA 相符
python -m fsl_history.research_cli \
  --manifest /path/to/private/epoch_manifest.json \
  --root /path/to/private/research \
  --private-output /path/to/private/audit.json
~~~

manifest_cli 會計算指定本地檔案的實際 SHA-256，採**私人路徑、只建立新檔而不覆寫**，並以機器時鐘記錄真正擷取時間；範例中的 EPOCH、Git SHA、模型修訂、路徑與時間必須由真實執行資料填入，不是可直接引用的實證紀錄。

真正要進行公開研究輸出時，需要提供 FSL_BRIDGE_EXPORT_KEY 作為本地環境變數，另行指定 public-output 的目的路徑。不得將密鑰、私人 manifest 或公開未經授權研究素材提交到公開 FSL。

## 6. 研究現況與未知

已完成：官方日期歷史事件、時間版本驗證、五家供應商的同期公告矩陣、過往 Arena／HF 分層觀測接入、AMRAL／FELRA 本地檔案證據及匿名化接口、負向測試及 GitHub CI 研究包。

尚未實證：多模型同品質 G1/G2 真正跨日任務、各訂閱方案真實額度與費用、完整 AMRAL/FELRA 獨立執行證據、已退役模型在其原時代的可信成功機率與總成本。這些不能拿現有公告日期或模型公司自評補造。

保留使用者後續提出的**另類資料**作為開放擴展方向，但目前不預先假設該資料的類型、數值結構或理論地位。

**核心原則：同一個人類目標，2024、2025、2026 的 AI 各自需要什麼工具、訂閱、時間、額度、人類介入與驗證成本，必須由當時條件與真實成果共同回答。**

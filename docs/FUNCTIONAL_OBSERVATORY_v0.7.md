# FSL v0.7 — Functional Mission Observatory：從工作歷程到可核查成果

**2026-11-07｜UTF-8 Markdown canonical source｜原創程式與文件 Apache-2.0**

## 1. Research position

FSL 的首要能力標準以使用者的功能性上界為準：
- G1：從真正需求開始，跨數天、數週、數月持續推進，直到完成可驗收的結果；
- G2：在 G1 前提下，知道何時應改變策略、何時維持、何時澄清及例外升級，最後完成使用者真正要的更新目標；
- G3：只需一輪或少數幾輪使用者實質指導，完成同時代頂級品質的完整、可用、可玩的遊戲或 App；
- G4：完整作品中的鮮明個人風格與有獨特形式的 AI-native 創作風格；它不必先達成 G3；
- E1：獨立具身 AI 軌道，一個系統跨不同實體任務領域辨識、切換及安全完成，與數位 G3 的完成度不等價。

只有 G2 明確依賴 G1。G3 與 G4 是獨立成品目標。舊版 H50/H80 是輔助量尺，不再定義上述能力上界。

**v0.7 不是另一套 Agent，也不是要求 Agent 依此學習的規則。** 它只在外部觀測真實執行器及產品工程環境，以免受測系統靠自我敘述取得高分。

## 2. Four distinct layers

1. **User intent and mission contract:** 原有 v0.6 任務規格、目標雜湊、所要求交付的作品類別，以及 AI 系統完整堆疊版本。
2. **Actual action history:** Agent 產生的進度、checkpoint、恢復、需求變更、策略決策、人類澄清、例外升級和最後交付事件。
3. **Independent source receipts:** 唯讀查詢 GitHub 官方提交／CI 執行／工作流程產物資訊，以及實際本地檔案的 SHA-256。收據有自己的取得時間、來源、證據強度及不可覆寫的 ID。
4. **External adjudication:** 檢查任務歷程、重播可玩的遊戲或運作中的 App、第三方藝術風格評審及具身安全測試。**目前 v0.7 不提供這一層的獨立認證。**

工作紀錄是一種主張；收據是另一種觀測；最終成品的真實能力則需要外部測試。不能把三者當成同一回事。

## 3. Evidence channels already implemented

| Evidence | Proven facts | What cannot be inferred |
|---|---|---|
| GitHub commit | 官方 API 核對 repo、提交 SHA、Tree SHA | 提交作者日期可被設定，無法證明跨日 AI 自主運作 |
| GitHub Actions | 官方執行 ID、所屬 repo、HEAD、狀態、結果、平台記錄日期 | CI 通過不代表 3A 遊戲完成、App 真正可用或用戶目標達成 |
| GitHub artifact metadata | 官方產物 ID、大小、所屬流程及是否過期 | 尚未下載並核對產物位元組，更不能證明作品品質 |
| Local workspace file | 明確工作根目錄內某檔案在採集時的位元組 SHA-256 | 檔案真正作者、產品整合、執行時品質和可信外部時間 |
| G1/G2/G3/G4/E1 events | AI 或評審聲稱的歷程與成果 | 沒有外部核查前不是獨立能力認證 |

GitHub workflow 的 created_at 是服務端活動記錄；Git commit 的 committer date 則不是可信計時。兩者都不等於「Agent 花了多久真正執行」。

首次第一方 pilot 使用 FSL 公開 repo 觀測三項：HEAD 提交、當下工作流程、README.md 的實際位元組 SHA-256。這是**真實資料取得的工程驗證**，不是連續數月 AI 自主完成度的實證。

## 4. New software

- fsl_observatory/registry.py：追加式 SQLite observer_sessions、observer_receipts、observer_links，並與既有 functional_runs/functional_events 共用資料庫。
- fsl_observatory/providers.py：GitHub 官方 REST GET only、嚴格 repo/commit/run 身分比對；本地文件在指定 root 內安全雜湊。
- fsl_observatory/audit.py：以指定 UTC cutoff 重播收據／連結及進度來源，分別統計來源時鐘、證據覆蓋與缺少的驗收。
- fsl_observatory/cli.py：執行註冊、收據採集、綁定、只讀第一方 pilot、獨立稽核。
- tests/test_observatory.py：以合成 GitHub API 回應離線測試資料完整性、時間、假來源、外部 Token、檔案路徑與 hash 不符等失敗情境。
- .github/workflows/observatory-pilot.yml：讀取權限最小化的官方 Actions 驗證，保存 90 天來源快照與資料庫，不向第三方 repo 寫入資料。

## 5. Practical local integration

Python 3.11+，不需第三方 Python 套件。

建立真正持續任務前，應先在 v0.6 登記一份 observational mission spec 與包含 runtime manifest SHA256 的 mission run。系統不會自動將合成資料轉成真實任務。

~~~bash
python -m fsl_functional.cli --db observations/mission.sqlite spec --file mission_spec.json
python -m fsl_functional.cli --db observations/mission.sqlite run --file mission_run.json
python -m fsl_observatory.cli --db observations/mission.sqlite session --id observe-001 --project EveMissLab/YourProject --mission-run YOUR_RUN_ID

# 在真實 Agent 工作進展後，先由它保存對應事件
python -m fsl_functional.cli --db observations/mission.sqlite event --file agent_checkpoint_event.json

# 接著觀測既有的 GitHub 提交、CI 或本地成果，均為唯讀
python -m fsl_observatory.cli --db observations/mission.sqlite github-commit --session observe-001 --repo EveMissLab/YourProject --sha COMMIT_SHA
python -m fsl_observatory.cli --db observations/mission.sqlite github-workflow --session observe-001 --repo EveMissLab/YourProject --run-id REAL_RUN_ID
python -m fsl_observatory.cli --db observations/mission.sqlite local-file --session observe-001 --root ./workspace --path build/game.zip

# 只有符合來源及雜湊的收據才可附到對應任務主張
python -m fsl_observatory.cli --db observations/mission.sqlite link --receipt RECEIPT_ID --event EVENT_ID --role supports_deliverable
python -m fsl_observatory.cli --db observations/mission.sqlite audit --session observe-001 --output observations/mission_audit.json
~~~

對 supports_deliverable，觀測檔案 SHA-256 必須等於事件宣告的交付 hash。對 supports_checkpoint 的本地檔案也會核對雜湊。supports_ci 只接受已完成且成功的 GitHub workflow。不同 mission 之間不能任意交換來源連結。更正是新增事件，舊事件不會刪除。

GitHub 的暫存 Actions Artifact 不是永久資料庫。**真實 G1 研究需保存同一 SQLite 和原始來源備份，跨實際日曆日持續錄入**，並避免把後來收集的資料假裝過去就已取得。

## 6. What is still NOT certified

本版本無法單憑 GitHub API、SHA-256、URL 或 JSON 宣稱：
- AI 已持續自主工作數個月；
- AI 已真正完成可玩且與人類頂級作品可比的 3A 開放世界遊戲；
- App 獲得真實市場驗證或確實解決目標使用者問題；
- 作品已證明 AI 獨特藝術風格與原創性；
- 具身 AI 已在不同現實環境安全完成多領域任務。

輸出中的 real_elapsed_autonomous_work_verified、real_finished_product_quality_verified、ai_only_causal_attribution_verified、G1_G4_or_E1_certified 在 v0.7 皆不能自動變成 true。

**這是刻意保留的研究嚴格性。** 下一版需要外部持續執行器、可信時鐘與跨日期 checkpoint、可重現的產品驗收工具、真人實測與獨立創作審查，才可能提升證據等級。

## 7. Next: v0.8

優先在同一持續任務中建立 G2 目標干預對照：需求真的改了要重新規劃、無關擾動時應保持、目標不清楚應澄清、特殊風險應升級；最後比較的是**完成變更後真正目標的結果**，不是 AI 說自己改變策略幾次。

同時以外部遊戲或 App 工程建置驗收作為 G3 小規模試點，但不得以單一漂亮渲染圖代替完整頂級作品。G4 有獨立美學與原創性評審，E1 有獨立具身多任務與安全門檻。

## 8. Rights and source integrity

專案原創程式與此 UTF-8 Markdown 採 Apache-2.0。第三方 API 資料不因此獲得同樣授權。GH Token 僅用於被允許的唯讀 GET，永不存入事件庫；本地檔案只做 bounded hash，不自動上傳內容。保留失敗、來源不匹配及無法判定的結果，避免用虛構數據補足能力證明。

**這一版本真正完成的是「觀測真實工程證據」，不是提前宣布「已達功能性智能上界」。**

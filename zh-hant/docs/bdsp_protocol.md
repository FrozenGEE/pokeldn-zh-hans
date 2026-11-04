---
title: 遊戲協議
parent: 晶燦鑽石與明亮珍珠
nav_order: 2
---

# BDSP 自己的協議，以及控制一個角色

BDSP 在它的 Pia 載荷裡跑一套帶型別的訊息協議。`TeamLumi/opendpr`（一份反編譯的 C# 復刻）中的
`Dpr.NetworkUtils.NetDataParser` 列出了每一條訊息：一個 `ANetData<T>`，用一位元組的 `DataID` 包住一個
普通結構體 `T`。標註 1.3.0 main 的地址位於明亮珍珠的映象中。

## 分幀

    0x0  1  data id
    0x1  2  payload length, big-endian
    0x3  .  the struct, little-endian, packed

`JoinData`（`byte, byte, byte, short, Vector3`）在線上是 17 位元組。

`NetDataParser` 註冊了 65 條訊息，全部在 `pokeldn/bdsp/netdata.py` 中（由
`scripts/gen_bdsp_netdata.py` 生成）。原始碼裡能確定 53 種佈局；有十二種帶 C# 的 string、陣列或列表
（`netdata.OPAQUE`），靠二進位制確定：載荷就是被 marshal 的結構體（`ANetData<T>.ConvertStructToBytes`
[main.bin 0x27bb0e0]），字串與陣列作為定長欄位，長度由 `Il2CppTypeDefinitionSizes` 與
`fieldMarshaledSizes` 決定，由 `CodeRegistration.interopData` 中的 `marshalToNative` 寫入
[1.3.0 main 0x4acd0c8]。抓到的載荷與之相符（`room.NATIVE_SIZES`、`room.MEASURED`）。

| id | 載荷 | 位元組 | 佈局 |
|---|---|---|---|
| 0x02 | `PosListData` | 72 | 12 個 `PosData`（ushort posX、ushort posZ、short rotY） |
| 0x13 | `TradePokeData` | 328 | 一個按存檔尺寸的加密 PB8 |
| 0x14 | `NetRecodeData` | 694 | `RECORD` 120、`RANDOM_SEED` 132、`TvRecodeData` 204、4 個 `TV_STR_DATA` 36、`RECORD_HEAD` 48、十個 int、六個位元組 |
| 0x15 | `BallDecoData` | 143 | affixSealCount、Is3DEditMode、IsAppliedTemplate，然後是 20 個 `SealParam{short x, y, z; byte id}` |
| 0x18, 0x54 | `UgSecretBase` | 616 | short zoneID、posX、posY；byte direction、expansionStatus；int goodCount；30 個 `UgStoneStatue` 20；bool isEnable（4） |
| 0x22 | `StanbyListData` | 20 | 5 個 `StandbyData`（isAddPlayer、hostIndex、myIndex、langId） |
| 0x24 | `TradeTranerData` | 32 | 13 個 UTF-16 字元、uint tranerId、byte cassetVersion、byte langId |
| 0x29, 0x61 | `UgStationID_to_DigFossilIDList` | 8 | `byte DigFossilIDs[8]`，0..7 的一個排列 |
| 0x38 | `BattleMatchingPokeData` | 481 | 一個 328 位元組的 PB8、20 個 7 位元組的 `SealParam`、uint attachPokemonId、uint attachPersonalRnd、byte index、num、is3DEditMode、isAppliedTemplate、affixSealCount |
| 0x42 | `NetPlayerName` | 28 | 13 個 UTF-16 字元、byte genderid、byte languageId |

`SendStandbyPlayerData` [1.3.0 main 0x01e52fa0] 用 `unionMatchWaitDataList` 填充 0x22；空列表是二十個
零位元組。站點用 `NetDataStandbyWaitData` 把自己加進去（0x59，同樣四個位元組，`isAddPlayer = 0` 表示
移除）：發出 `59 0004 01 00 01 03` 之後，下一條 0x22 是 `22 0014 01 00 01 03` 加十六個零。螢幕不會有
變化。

marshal 過程不清空緩衝區：定長欄位在它的值之後帶著堆殘渣（[交換頁](bdsp_trade.md)）。

## 空口上出現過什麼

獨佔房間的主機發送 `NetJoinData`（0x01，可靠，17 位元組）、`NetPosData`（0x02，不可靠，72）、
`NetRequestData`（0x12，1）和 `NetDataIsMatchWaitData`（0x23，可靠，1）。收到請求時它還會發 0x09 和
0x22；有活動時發 0x14 和 0x15。交換訊息見[交換頁](bdsp_trade.md)。一條 0x23 可能藏在一個存在位元組
0x00 之後；走一遍訊息時必須把 0x00 也當作一條訊息（[訊息分幀](pia.md#message-framing)）。

## 主機會重複傳送的訊息

`NetJoinData` 就是 `JoinData` 的全部：

| 偏移 | 大小 | 欄位 |
|---|---|---|
| 0x00 | 1 | `avatarId`（[模型](#the-model)） |
| 0x01 | 1 | `colorId`，0 |
| 0x02 | 1 | `cassetVersion`，0x31 |
| 0x03 | 2 | `InitRotY`，度，小端，非對齊 |
| 0x05 | 12 | `InitPos`，三個小端 float，x、y、z |

`NetRequestData` 是一位元組，即想要的 id。主機會反覆請求 0x23，直到客戶端確認它的可靠視窗；它建立一個
角色時會請求 `NetCharacterStateData`（0x04）：一條 0x04 請求意味著角色已經存在，`bin/bdsp_connect.py`
把它當作判定依據打印出來。

`UnionRoomManager$$SetNetData` [1.3.0 main 0x01e50700] 應答六個 id 的請求，其餘忽略：

| 請求 | 主機發送 |
|---|---|
| 0x01 `NetJoinData` | 它的加入記錄 |
| 0x04 `NetCharacterStateData` | 它的角色狀態 |
| 0x09 `NetDataBattleTypeData` | 它的對戰規則 |
| 0x13 `NetTradePokeData` | 它提供的寶可夢；沒有選中時什麼也不發 |
| 0x22 `NetDataStandbyWaitListData` | 它的待機列表 |
| 0x23 `NetDataIsMatchWaitData` | 它是否在等待匹配 |

應答走可靠流，在 30 到 130 ms 內到達房間裡已有角色的站點。

### 壓縮

可靠頭部的標誌 0x10 表示整個遊戲訊息（含頭部）是一條 zlib 流。`ReliableSlidingWindow` 的 push
[1.3.0 main `0x15a10d0`] 在視窗的開關（+0x7ac）開啟時做 deflate，結果沒有變小時就發原文
（`0x159a5b0`）。產生的位元組等於 Python 的 `zlib.compressobj(5, zlib.DEFLATED, 12, 5)` 加一次 sync
flush 再 finish。加入訊息發原文；記錄（0x14）、球殼（0x15）和全零的 0x22 會變小。`bin/bdsp_connect.py`
按這個標誌決定是否解壓。

### 其餘不透明訊息的傳送方

| id | 類 | 傳送方 |
|---|---|---|
| 0x14 | `NetDataRecodeData` | `RecodeMatching$$SendRecodeData`、`UnionStateController$$SendRecodeData` |
| 0x15 | `NetDataAttachSealNetData` | `BallDecoMatching$$SendBallDecoData` |
| 0x18 | `NetSecretBaseData` | `UgNetworkManager$$SendMySecretBaseData`；按請求傳送 |
| 0x61 | `NetDigTableData` | 按請求傳送 |
| 0x38 | `NetDataBattleMatchingSelectPokemon` | `BattleMatchingManager$$SendSelectPokemonData` |
| 0x42 | `NetPlayerNameData` | `UgNetworkManager$$SendOnJoinNewPlayer`、`SendPlayerNameData` |
| 0x54 | `NetSecretBaseUpdate` | 沒有可靠的傳送方 |

### 不可靠流

| 位元組 | 訊息 |
|---|---|
| `04 0002 00 00` | `NetCharacterStateData{NONE, 0}`，每兩秒一次 |
| `12 0001 04` | 請求 0x04 的 `NetRequestData` |
| `02 0048 <72 B>` | 角色行走時的 `NetPosData` |

`room.build_state()` 和 `room.build_match_wait(False)` 構造狀態與 0x23 的應答。主機會每秒重傳一條可靠
訊息五次，直到被確認；比它最後一個序列還多出兩個的確認會被忽略。

## 傳送遊戲會照做的訊息

可靠序列 id 與主機自己的傳送共享；低於已確認 id 的訊息會被靜默丟棄。每次傳送前立刻讀取該 id。一臺
零售明亮珍珠會照做落在它自己最後一條訊息那個 id 下的回覆，而丟掉 id 更低的回覆：在它的狀態訊息（27）
和它的寶可夢（28）之後，一條 27 之下的迴歸寶可夢被確認了，卻從未被檢查。落在已確認序列上的加入會被
照做；`--room-pattern fixed` 在第一條 0x04 請求處停止，`--join-wait` 以秒為間隔（預設 1.0）。

`UnionOpcManager` 在每次加入時呼叫 `CreateCharacter(joinData)`：四十次加入就是四十次登場。背後沒有
會話的角色會跟著玩家跨地圖，直到遊戲重啟。`OpcManager$$RemoveCharacter` [0x02279ee4] 接收一個站點
索引。

## 角色記錄

`OpcManager.CharaData` 是
`{int stationIndex, string assetName, int colorId, int avatarId, int sexId, int cassetVersion}`，以站點
為鍵。

### 模型

    NetJoinData.avatarId  ->  CreateCharaData  ->  CharaData.avatarId
                          ->  UnionCharacterTable.SheetSheet1{ID, AssetName}
                          ->  OpLoadCharacter("persons/field/" + assetName)

`CreateCharaData` [1.3.0 main 0x022796b0] 設定 `sexId = avatarId > 7 && avatarId != 16`：8 到 15 是
女孩，0 到 7 和 16 是男孩。8 是女孩，0 是戴藍帽子的男孩（`--join-avatar N`）。

主機自己的加入攜帶 work 360（`GetAvaterId` [0x01e54030]）。新存檔裡是 0。外觀計數器
（`ev_union_character_select_*`）對男孩存 16 或 1 到 7，對女孩存 8 到 15；否則，在 work 360 為 0 時，
`ev_traner_other_see_random` 把它設成 1 + 一個小於 16 的隨機值，性別隨機。所以只有當這個計數器被用過
之後，加入訊息才會帶上存檔的性別。

`NetDataTranerCardData`（0x05，75 位元組）在聯盟室裡什麼也不繪製。

### 狀態位元組

`StateData` 是 `{byte state, byte isRecruiment}`，`state` 是一個 `OpcState.OnlineState`：

| 值 | 名稱 | 值 | 名稱 |
|---|---|---|---|
| 0 | `NONE` | 5 | `RECRUITMENT_RECORD` |
| 1 | `DIG_FOSILL` | 6 | `RECRUITMENT_GREETINGS` |
| 2 | `SECRETBASE_ACTION` | 7 | `RECRUITMENT_BALL_DECORATION` |
| 3 | `RECRUITMENT_BATTLE` | 8 | `COMMUNICATE` |
| 4 | `RECRUITMENT_TRADE` | | |

17 到 21 是 `NOW_*` 狀態（[transitionType 表](#talkstate-and-the-value-that-crashes-the-game)）。
`RECRUITMENT_*` 的值會豎起一個對話氣泡：`StateData{RECRUITMENT_TRADE, 1}` 顯示交換氣泡。

收到的 0x04 到達 `UnionOpcController$$SetNetData` [1.3.0 main 0x01e48c50]（站點沒有角色時被丟棄），
它設定狀態，按 `isRecruiment` 選主持表情或普通表情，並在狀態非零時播放動畫 0。遠端角色的狀態只會在
它自己的站點發來 0x04 時、或它被移除時改變。在該角色的 `Start` 執行之前，setter 會丟掉這個值
[0x02277c50]，而 0x04 請求在它之前就發出去了 [0x01e49854]：所以要像主機那樣每兩秒重發一次狀態。

`OnlinePlayerCharacter$$IsCanTalkState` [0x02277af0]：狀態 1、3 到 8、17 到 21 可以搭話。

### 行走

主機自己的 `NetPosData` 每 0.410 s 一次，跨 0.935 單位（`room.POS_PERIOD`、`room.POS_STRIDE`）。
`pos = (-posX * 0.05, posZ * 0.05)`。遠端角色會與牆碰撞；玩家不會與它碰撞。`--room-walk-steps 8`
會留在房間內；交換不需要走動（`--room-walk-steps 0`，交換路徑的預設值）。

## 被搭話

掛著表情的玩家會停在原地等人靠近，狀態非零時按 A 什麼也不做。交換表情是
`NetCharacterStateData{4, 1}`，用 `{0, 0}` 清除。用 `isRecruiment` 做閘門：狀態 18 是已經進入交換的
主機。

搭話是 `NetDataTalkReserveData`（0x63），`63 00 01 00`（`bin/bdsp_connect.py --initiate-talk`；
`bin/bdsp_host.py --approach-delay`）。主機靠近客戶端時：

    cli ->  64 0003 00 01 04      NetDataTalkReserveResultData{IsCanTalk, IsRecruitment, emoticonStateType}
    con ->  06 0005 00 01000000   NetDataTalkData{talkOpcSexId: 0, talkState: GREETING}
    con ->  10 0002 01 04         NetDataTalkCancelEndData{IsRecruitment: 1, emoticonStateType: 4}

沒有 0x64，玩家就一直僵著。`IsCanTalk` 為 0 會跑問候並把它停在「one second!」上；為 1 則顯示
「sorry, I have other plans」。丟掉該站點會釋放被停住的問候。

### 主機主動靠近

`UnionRoomManager$$MyUpdate` [1.3.0 main 0x01e49fb0] 只在玩家狀態為 0、沒有對話或視窗開啟、且玩家
在所有 `EnterCollision` 之外時才處理 A 鍵。對 10.0 單位內最近的角色：

| 角色的狀態 | A 鍵做什麼 |
|---|---|
| 0、2、9 到 16 | 什麼也不做 |
| 8、17 到 21 | `StartTalk(opc, 0, 0, 0)` [0x01e4c2d0] |
| 4 | `CheckErrorMessageTrade`，然後同最後一行 |
| 7 | `CheckBallDeco`，然後同最後一行 |
| 1、3、5、6 | 傳送 0x63，把狀態存進 `nowTalkReserveState`（+0x188），`CreateSelectStateModel(state, 1)` |

主機讀到 0x64 時 [0x01e50dec]，除非 `emoticonStateType` 等於 `nowTalkReserveState`（那就把它清掉），
否則傳送 `NetDataTalkCancelEndData{0, 0}`；所以一個對外宣稱 `{4, 1}` 的角色會用 `64 0003 00 01 04`
作答，每條 0x63 一次，忽略重傳的副本。

當主機是搭話的一方時，客戶端的角色就是招募者。招募者的「是」是 `NetDataTransitionData{18, 0}`，即
`07 0002 12 00`（[交換頁](bdsp_trade.md#the-message-sequence)）。在 0x64 之後傳送它，會在搭話的主機上
開始交換，而無需它自己的玩家點「是」（`SwitchTransitionMessage` [0x01e53bf0] -> `TransitionTradePoke`
[0x01e5c1c0]）：主機會發出它的 0x24 並開啟交換盒。`SwitchTransitionMessage` 讀取該型別的模型時沒有
空指標檢查；若一條 0x07 發給自進入以來沒在交換招募者上按過 A 的主機，就會穿過空指標讀取。

### 問候裡的名字

問候用角色所在站點的 Pia 玩家名來稱呼它（`NetworkManager$$GetGamerData` [1.3.0 main 0x02250e50]），
從 PlayerInfo 按 UTF-8 解碼。當名字為空、被 `CheckNgWords` 標記、或按 UTF-16 單元超過該語言的上限時，
`Utils$$CheckNGTrainerName` [0x01cbdc30] 會替換成一個版本名：

| `lang` | 上限 |
|---|---|
| 1、8、9、10 | 6 |
| 任何其他正值 | 12 |
| 0 或以下 | 由介面的當前語言決定 |

PlayerInfo 是 195 位元組（解析器 [0x0154f044..0x0154f5e0]）：

| 偏移 | 欄位 |
|---|---|
| 0x00 | 名字編碼：2 表示 20 個 UTF-16 單元，其他值為 80 位元組 |
| 0x01..0x50 | 名字 |
| 0x51 | 第二個字串的編碼 |
| 0x52..0x79 | 第二個字串，40 位元組 |
| 0x7A | 語言，一個 `MsgLangId` |
| 0x7B..0xBA | 64 位元組 |
| 0xBB..0xC2 | u64 |

    MsgLangId  JPN 1, USA 2, FRA 3, ITA 4, DEU 5, ESP 7, KOR 8, SCH 9, TCH 10

主機在 0x7A 處傳送它的遊戲文本語言（存檔 `CONFIG.msg_lang_id`，`get_msgLangID` [0x0237e100]），以及它
檢查過的名字，編碼 1。站點協議的寫入方把它放在那裡 [0x01550e98]。`bin/bdsp_connect.py` 和
`bin/bdsp_host.py` 用 `pokeldn/bdsp/host.py` 的 `player_info` 構造 PlayerInfo 併發送 `--language`，
預設 3；桌面應用傳的是自己的訓練家語言。在 3 之下，11 個字元的名字會完整顯示。在 1 之下，一臺零售法版
明亮珍珠把 11 個字元的名字顯示成「Perlo.」，問候是「Konnichiwa!」。

替換用的名字取決於被搭話角色 `NetJoinData` 的第 2 個位元組：0x31 用 `dp_characters` 的第 247 號標籤，
其他情況用第 206 號，再加一個句點：

| bundle | 0x31（明亮珍珠） | 其他值 |
|---|---|---|
| english | `Pearl.` | `Diamond.` |
| french | `Perlo.` | `Diamant.` |
| german | `Perl.` | `Diamant.` |
| italian | `Perl.` | `Diaman.` |
| spanish | `Perla.` | `Diamant.` |
| jpn, jpn_kanji | `パール.` | `ダイヤ.` |
| korean | `펄.` | `다이아몬드.` |
| simp_chinese | `帕爾.` | `戴亞.` |
| trad_chinese | `帕爾.` | `戴亞.` |

### talkState，以及會讓遊戲崩潰的那個值

`TalkState` 是 `{CHECK = 0, GREETING = 1, NONE = 2}`。CHECK 會讓
`UnionStateController$$SwitchSpokenStateMine` 在沒有空指標保護的情況下解引用 `msgWindow`
（0x1fd5ec0）；掛錶情站著的玩家沒有這個視窗，所以 CHECK 會讓遊戲崩潰。`pokeldn/bdsp/room.py` 拒絕
傳送它。

`NetDataTransitionData{transitionType, isRecruitment}`（0x07）把停住的問候推進成一項活動。它是以尾呼叫
發出的，只掃 BL 指令的呼叫方掃描看不到它（[查詢呼叫方](switch_re.md#finding-callers)）。
`SwitchTransition` [1.3.0 main 0x01e5ba70] 按它分發：

| transitionType | 活動 | 進入方式 | `UnionStateController` + 處的模型 |
|---|---|---|---|
| 3、17 | 對戰 | `TransitionBattle` | 0x38 或 0x40，看 `isRecruiment` |
| 4、18 | 交換 | `TransitionTradePoke` | 0x50 |
| 5、19 | 記錄混合 | `RecodeMatching$$Open` | 0x60 |
| 6、20 | 訓練家卡片 | `TransitionShowTrainerCard` | 0x70 |
| 7、21 | 球殼 | `BallDecoMatching$$Open` | 0x80 |
| 8 到 16 | 無 | | |

`RecodeMatching$$Open` 和 `BallDecoMatching$$Open` 會立刻把主機自己的記錄發出去然後等待；只有對方的
記錄才會寫入存檔。

### 記錄混合

主機用「Échanger des données」（狀態 5）招募。自己的玩家點「是」之後，它傳送
`NetDataTransitionData{5, 0}`，然後是 694 位元組的 `NetDataRecodeData`（zlib），並停在狀態 19 等待。沒人
應答時，它約 44 s 後回到房間。`room.parse` 把記錄的頭作為 `recode` 返回：

    RECORD.record[30]        thirty uint counters indexed by RECORD_ID
    RANDOM_SEED              group_name (16 chars), name (32 chars), int sex, int region_code,
                             ulong seed, ulong random, long time_stmp (FILETIME), int user_id
    TvRecodeData             five TV records, each `bool isEmpty` (4 bytes), ints, a TV_STR_DATA
    4 x TV_STR_DATA          {16-char value, byte language, genderId, two reserved}
    RECORD_HEAD              13-char username, int language, byte sex, int body_type, uint uniqueID
    ten ints, six bytes      per-TV branch values, myVersion (0x31), five *IsNotEmpty flags

未寫入的欄位裡是堆指標。`RECORD_HEAD.sex` 與 `RANDOM_SEED.sex` 可能不一致。

### 對戰階梯

一場對戰（招募時狀態為 3）走一段階梯；招募的主機在每一級上都等加入方：

| 加入方傳送 | 主機做什麼 |
|---|---|
| `NetDataTalkData{GREETING}` | 顯示「Un combat ? OK !」並等待 |
| `NetDataSelectData{0}`（0x08） | 顯示「... est en train de choisir quoi faire...」並等待 |
| `NetDataBattleTypeData{0}`（0x09，Single） | 問它自己的玩家；點「是」後傳送 `NetDataTransitionData{17, 0}` 並開啟大廳 |
| `NetDataBattleMatchingJoin`（0x30）`{uint id, byte stationIndex, index, language, colorId, avatarId, sexId, cassetVersion}` | 用自己的加入訊息作答並轉發加入方的；加入方出現在第二個槽位 |
| `NetDataBattleMatchingReady`（0x32，空） | `NetDataBattleMatchingState{0, 6}`（0x33，`SelectBattleTeam`） |
| 什麼也不發 | 在選好隊伍時發六條 0x38，然後「en attente d'autres personnes」 |

每條 0x38 裝一個加密 PB8（按順序的已選隊伍），殘渣裡的貼紙 `affixSealCount` 為 0，`index` 為 0 到 5，
`num` 為 6。沒有找到對 0x30 `id` 的任何檢查。`MatchingState`：None 0、Initialize 1、Load 2、
RecruitmentMember 3、SelectTeamMember 4、SelectRule 5、SelectBattleTeam 6、SelectPokemon 7、
GoBattle 8、Result 9、Resume 10、Closing 11、LeavedOtherMembers 12。

`NetDataSelectData`（0x08）是 `{byte index}`；它的接收方 [0x01e52a30] 忽略 index，把
`UnionStateController+0x38`（對戰招募模型）驅動到 `BATTLE_RULE_SELECT_WAIT`，不管當前開著哪個對話，
也沒有空指標檢查。該模型只在玩家招募一場對戰時才被設定，並且在每次進入聯盟室時都是空的
（離開房間的各區域時 `UnionRoomManager` 會被銷燬，`NetUseManager.OnZoneChange` [0x026cfef0]）。
按這種讀法，向本次進入還沒招募過對戰的主機發 0x08 會寫到地址 0x18 [0x023e2604]。一臺從未招募過的
零售明亮珍珠在其交換盒上和訓練家卡片交換時都確認了 `08 00 01 00`，螢幕沒有變化；接收方究竟有沒有執行
並不清楚。除非主機自己的 0x04 表明狀態 3 且 `isRecruiment` 為 1，否則永遠不要發 0x08。

### 地下大洞窟

地下在場景 id 12608 下廣播同一個 `local_communication_id`；同一套會話程式碼就能關聯，不需要加入記錄
（`--room-walk 0`）。站點到來時 `UgNetworkManager` 傳送：

| id | 類 | 位元組 | 內容 |
|---|---|---|---|
| 0x17 | `NetZoneData` | 16 | `Vector3 pos`、`int zoneID` |
| 0x42 | `NetPlayerNameData` | 28 | 13 個 UTF-16 字元、byte genderid、byte languageId |
| 0x50 | `NetKousekiCount` | 4 | `int Value` |
| 0x41 | `NetSecretBaseInfo` | 16 | 在秘密基地內部代替 0x17：入口的 `Vector3 pos`、`int zoneID` |

一條指明玩家所在區域的 `NetUgJoinData`（0x16，18 位元組：
`byte avatarId, colorId; short zoneID, InitRotY; Vector3 InitPos`）會把一個角色放到玩家旁邊；主機會
請求它的 0x04 和 `NetNaminoriData`（0x55），並每 0.41 s 發一次 `NetPosData`
（`--ug-join --room-walk-steps N`）。

`UgNetworkManager$$OnReceiveRequestData` [1.3.0 main 0x01f7c050] 應答對 0x01、0x04、0x18、0x19、
0x54、0x55 和 0x61 的請求——前提是主機的視窗已經承載過東西：

| 請求 | 位元組 | 內容 |
|---|---|---|
| 0x18、0x54 | 616 | 玩家自己的 `UgSecretBase`；其 `zoneID` 為 0 時什麼也不發 |
| 0x61 `NetDigTableData` | 8 | 挖掘化石表，0..7 的一個排列，就緒之後才有 |

非主持的站點在加入時請求 0x61。`OnReceiveDigTableData` [0x01f7dad0] 在其表標誌（+0xA8）為 0 期間
採納第一條到達的 0x61，不看是哪個站點發的，也不做檢查，重建挖掘點並置位標誌；之後的都被忽略。
`CreateDigPoints` 用 `MyStationIndex` 索引該表，並不做空指標檢查地查那個組 id：只發 0..7 的排列，
因為更大的位元組會讓主機出錯。每個 `UgFieldManager` 會話都會新建一個 `UgNetworkManager`，所以每次都
重新採納一張表。0x29 `NetDigGroupIdData` 既沒有傳送方也沒有接收分支。

`bin/bdsp_connect.py --inject-file PATH` 會可靠地傳送檔案中每一行新的 `ID:HEX`。

### 球殼

主機用「Déco Capsule」（狀態 7）招募。它傳送 `NetDataTransitionData{7, 0}`，進入狀態 21，然後傳送
143 位元組的 `NetDataAttachSealNetData`（zlib）。沒人應答時，它約 45 s 後回到房間。若用 143 位元組應答
（`bin/bdsp_connect.py --answer-with 0x15:FILE`），它會應用這些資料並回到房間。應答要從自己的任務裡
發出：在接收方內部發時，它等待的確認永遠讀不到。

`BallDecoMatching$$ReceiveBallDecoData`（`0x021ca5e0`）寫入 99 個球殼槽位中第一個沒有貼紙的，若全都
有貼紙就什麼也不寫。`BallDecoWork$$CopyTradeCapsuleData`（`0x01f23eb0`）清空該槽位，並在存檔裡有現貨時
把每個貼紙放到 `(x, y, z) / 100`，同時消耗掉它，否則丟棄。所有貼紙都放好時收尾訊息是
`DLP_net_union_room_090`，否則是 `_114`。數量超過 20、或貼紙 id 為 200 及以上會拋異常。

位置是球殼半徑的百分之一。3D 模式把每個貼紙畫在它所在的位置。2D 模式只在網格單元的
`BallDecoWork$$Convert2DPosition`（`0x01f24da0`）處畫貼紙：半徑 1，正面（+z）行列間隔 28 度，背面
25 度，每個分量取整到 0.01。正面和背面的網格都是 7 × 7 的方格減去 `(|x|, |y|)` 屬於
`{(3, 2), (2, 3), (3, 3)}` 的部分（`Capsule2DViewController$$Initialize` `0x01e909b0`，零售
1280 × 720 縮放）：

    row  3   columns -1..1
    row  2   columns -2..2
    row  1   columns -3..3
    row  0   columns -3..3
    row -1   columns -3..3
    row -2   columns -2..2
    row -3   columns -1..1

落在網格之外的 2D 設計會佔用一個標記為已裝飾的槽位，但什麼也不畫。

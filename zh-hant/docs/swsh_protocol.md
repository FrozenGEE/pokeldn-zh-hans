---
title: 同步框架
parent: 劍與盾
nav_order: 2
---

# 訊息、內容與路由

Pia 之上的釋出/訂閱框架。一條訊息是一個 u16 小端 id、一個鑑別位元組、一個零位元組，以及一個 protobuf 體。

## 訊息 id 從哪來

低位 id 來自 `0x01BBFFA0` 處一張 838 條 24 位元組記錄的表，`{u64 handler 槽, u32 0x402, u32 id, u64 0}`，id 為 1..880。高位 id 是基址加偏移。

## 內容與持有者

每個內容註冊三個持有者（註冊器 `0x010ccd90` 內容 30、`0x010da7d0` 40、`0x010d5150` 50），給它的偏移 `ldrh [content+0x372]` 加上一個基址，再把每一個傳給 `0x006daeb0(manager, &holder, flag)`：

| id | 持有者 | flag |
|---|---|---|
| 10000 + 偏移 | `0x010dd910` | 1 |
| 20000 + 偏移 | `0x010d85f0` | 0 |
| 30000 + 偏移 | `0x010d0980` | 0 |

40000 那一族是在更低一層鑄出來的（`ldrb w20,[x0,#0x28]`、`add w24,w20,#-0x63c0`、`strh w24,[x20,#0x160]`）：40030 / 40040 / 40050。

沒有監聽者的持有者會靜默丟棄（`0x010d81d0`）。沒有任何東西會到內容 40 或 50 的 20000 基持有者：20040 與 20050 是惰性的。

### 30000 持有者

30000+偏移那個持有者（`0x010d0980`，vtable GOT `0x02618620` = `0x02528100`，無 RTTI）攜帶的是 `gflnet.p2p.framework.pb.SequenceDataHolder`：

    SequenceDataHolder    oneof message {
                             1 CancelAccepted        cancelAccepted
                             2 RequestCancel         requestCancel
                             3 RequestCancelAll      requestCancelAll
                             4 RequestForcedProceed  requestForcedProceed }
    CancelAccepted        { 1 int32 currentSeqNo; 2 bool  isForced    }
    RequestCancel         { 1 int32 currentSeqNo }
    RequestCancelAll      { 1 int32 currentSeqNo }
    RequestForcedProceed  { 1 int32 currentSeqNo; 2 int32 targetSeqNo }

解析器 `0x006a7580`；接收（槽 8 `0x008b9590`）呼叫 `[holder+0x168]` 的監聽者槽（case - 1）。盾 1.3.2 只構造 CancelAccepted（`0x006a3db0`，由傳送包裝 `0x008b7420` 和十個同步內容裡各兩個回覆任務呼叫）。正版交換從不帶 case 2 到 4；但主機收到仍會照做（見[內容 40](swsh_trade.md#the-cancel-and-proceed-messages)）。內容 40 的例項，30040，埠 0：

    RequestForcedProceed{c, c+1}   58750000 2204 08<c> 10<c+1>     c=0: 58750000 2204 0800 1001

### 三個交換內容

`0x010c9280` 建立會話：內容 30（盒子交換）在 `+0x120`，內容 40（SyncSaveDataHolder）在 `+0x148`，內容 50（PokemonTradeDataHolder）在 `+0x2b0`；自己的寶可夢 `+0x68`，對方的 `+0x70`；交換狀態（1..10）`+0x140`，錯誤碼 `+0x144`；`+0x418` 在第一幀發命令 3，而 `+0x419` 是抑制它的角色位。內容 50 以狀態 1 初始化，內容 40 以狀態 6 初始化。

## 路由路徑

    0x006a9a20   同步泵，來自交換會話的更新
    0x006db3b0   輪詢：對每條已註冊條目，抽乾它那種型別的兩個流（位元組 +8）
    0x006a8490   流 A：mesh 埠 [pia+0xd0+kind*4]，Pia 協議 0x7C
    0x006a84f0   流 B：mesh 埠 [pia+0xd8+kind*4]，Pia 協議 0x80
    0x006db9c0   抽乾：槽 0x78 填入 (傳送者*, 長度) 與 manager+0xf0 處的緩衝
    0x006db620   派發：匹配條目，呼叫持有者的槽 8
    0x010d81d0   內容 50 的 10000 基持有者：解析，呼叫監聽者的槽 0
    0x010d5e40   監聽者：傳送者轉站點索引，memcpy 0x158，呼叫

### 應用層頭

一段負載是 `struct.pack("<HBB", id, discriminator, 0)` 後面接訊息體，由 `0x006db840` 構建、`0x006db620` 解析。鑑別位元組是個世代計數（`[content+0x370]`，+1 模 255，`0x008b6670`），被推進 `[manager+0x480f0]`；一次強制的 CancelAccepted 會在內容 40 上讓它加一（`0x006db470`），而各註冊器會把它清零（`0x010d53a0`）。沒有強制 CancelAccepted 的交換全程都是零。

### 線上讀取登錄檔

    manager = read_u64(read_u64(main + 0x02616750))     0x006a9a70，輪詢的呼叫者
    count   = read_u64(manager + 0xD8)                  0x006db3dc
    array   = read_u64(manager + 0xD0)                  0x006db3e0
    entry i = array + i * 0x10                          0x006db3e4
    id      = holder's vtable slot 7, called at 0x006db740 (`ldr x8, [x8, #0x38]`)

槽 7 返回 `[holder+0x160]`。閒置畫面上這張表是空的；坐下的連線交換會加兩條；神秘禮物不加。

### 派發閘門、埠與傳送者

一條條目是 16 位元組：holder、+8 處的 kind、+9 處的 flag（只有 10000+偏移 才是 1）：

    id == holder->slot7()
    entry[8] == the drain's kind
    entry[9] ? header[2] == [manager+0x480f0] : no check

Kind 就是 mesh 埠：內容持有者為 0（20030、10050、ping），40000 族為 1（`0x006daf40(manager, &holder, 1, 0)`）。傳送者是一個傳輸指標，由 `0x006b5850` 解析（`mesh->GetStationIndex`，失敗為 0xfd）；迴環傳的是 `[[0x2616a30]]+0xf0`。`Data.ownerId` 在 10050 上不起作用。

## `Data` 信封

`gflnet.p2p.sync.pb`、`data.proto`：

    1  uint32  syncId        內容偏移        30 / 40 / 50
    2  uint32  elementId     基址            10000 / 20000
    3  uint64  ownerId       傳送者
    4  uint64  clock
    5  bytes   body          一對裡四個位元組；40050 裡是 344 位元組的 PK8

40000 持有者的監聽者是 `element+0x18`；它的槽 0，`0x006d59f0`，這樣路由：

    [Data+0x14] == [listener+0x10]        syncId，元素的偏移
    walk [listener+0x28] .. [+0x30]       子元素，每個 0x90 位元組
      [Data+0x18] == [sub+0x62]           elementId，u16
      [Data+0x20] == [sub+0x68]           ownerId，u64
    sub->vtable at 0x48 (sub, body, len, [Data+0x28])     body 與 clock
    otherwise: ret                        靜默丟棄

### 子元素種類

| 種類 | 建構子 | vtable | 出生時 `+0x88` | 槽 9，接收：長度檢查，存到 `+0x88` |
|---|---|---|---|---|
| 32 位 | `0x006d5c00` | `0x2512bc8` | 0 | `0x006d5f20`：4 位元組 |
| 對（相位） | `0x006d6160` | `0x2512c90` | `0xfc18fc18` | `0x006d6490`：4 位元組 |
| 16 位 | `0x006d66d0` | `0x2512d58` | 0 | `0x006d69f0`：2 位元組 |

一次接收隨後把 `[sub+0x78] = clock`，並 `strh 0x0100 -> [sub+0x60]`（就緒位元組 `+0x61`）；槽 7，也就是雜湊值，返回 clock。建構子接受元素 `x0`（`+0x80`）、elementId `w1`（`+0x62`）、ownerId `x2`（`+0x68`）、flag `w3`（`+0x70`）。

同步元素（`0x006d3f80`）每個同步內容構建一次（內容 30 在 `0x010ce604`，50 在 `0x010d6904`，40 在 `0x010dc264`）。vtable 來自 `0x2512b28`：

| 偏移 | vtable | 角色 |
|---|---|---|
| `+0x00` | `0x2512b38` | 主，6 個槽；2、3、4 是三個建構子，w3 = 1 |
| `+0x08` | `0x2512b78` | 介面 A：32 位那種 |
| `+0x10` | `0x2512b90` | 介面 B：對與 16 位那種 |
| `+0x18` | `0x2512bb0` | 路由監聽者，槽 0 = `0x006d59f0` |

鑄造 `0x006d44e0` 建四個通道：`+0xd0` 每個站點一個 32 位子元素，elementId 10000（法定人數雜湊）；`+0xf0` 在 `+0x38` 處一個 16 位子元素，elementId 20000、owner 0（就是[共享值](swsh_trade.md#the-phase-is-the-elements-field)），並每站點一個對，elementId 20000；`+0x110` 是法定人數雜湊所遍歷的那張表。

### 法定人數雜湊

elementId 10000 上的那四個位元組，由 `0x006d7b40` 在 `element+0xa8` 構建：

    h = 0
    for sub in subs:
        if (!sub[+0x61]) { h = 0; break }        任一站點未就緒 -> 零
        h = crc32(le32(h + sub->slot7()))        槽 7 就是 clock

非零表示每個站點都就緒了。`0x0065de30` 是 `zlib.crc32`；`0x0065df04`（多項式 `0x8005`）是 CRC-16。被遍歷的表 `element+0x110` 是 `0x006d48b0` 對 `+0x40` 的複製，保留 `+0x68` 為零的條目。

這條鏈覆蓋傳送者的 elementId 0 和 1（無 owner），然後是它自己的 elementId 20000。主持中的劍的非零雜湊能對得上，例如內容 50：

    elementId 0, no owner      clock 2304   主機自己的寶可夢（344 位元組）
    elementId 1, no owner      clock 2313   對方的寶可夢，被送回去
    elementId 20000, host      clock 2278   它那一對移動後變成 2338
    crc32 chain                8ffa0f2e     然後 b3615e90

把主機的雜湊回顯回去的加入方，就能對著主持中的劍完成一次交換。

## 協議 0x84 上的隊伍負載

`ReliableBroadcastProtocol` 把 3456 位元組的交換快照分三片傳送直到被確認；第三片是 zlib（Pia flag 0x10）：原始 1404 + 1404 + 157，最後一片解壓後為 648。`trade_payload.py` 拒絕任何別的總長。佈局（同 `kwsch/PokePiaSWSH`、`lincoln-lm/swsh-lan-client`）：

    0x000  六條 PK8 記錄，隊伍形態，每條 0x158          -> 0x810
    0x810  u32   隊伍數量
    0x814  MyStatus，272 位元組      TID/SID 在 0xA0，訓練家名在 0xB0
    0x924  TrainerCard，456 位元組   訓練家名在 0x00，存檔開始日期在 0x170
    0xAEC  玩家檔案，266 位元組                             -> 0xBF6
    0xBF6  392 位元組，對戰競技場塊；連線交換時為零
    0xD7E  2 位元組填充                                    -> 0xD80 = 3456

MyStatus 與 TrainerCard 是 PKHeX 的存檔塊（`Saves/Substructures/Gen8/SWSH/`）。構建者是 `0x0110c180`，接收者是 `0x0110cff0`。連線交換（`0x010967f0`）與密碼匹配（`0x00bd80f4`）不傳對戰競技場塊；對戰競技場（`0x00b2d7d0`）會傳一個。

### 對戰競技場塊

0x180 位元組資料，外加一個 u64 長度；讀取者 `0x00b2d9fc` 要求長度為 0x118。生產者 `0x00b2eb60`。從 0xBF6 起：

    0x000  u32    0x22fc 位元組規則核心（0x008ff9e0；regulation_preset_core_%d.bin）的 CRC-16（0x8005）
    0x004  0x100  隊伍簽名：match+0x98 處 0x136 位元組隊伍描述的 +0x36
    0x104  4      零
    0x108  u64    管理器的 optional（值 +0x1ab8，標誌 +0x1ab0），除非比賽型別 3 否則為零
    0x110  u8     當 0x00adb920 產出物件且 0x00b1ce10(0) == 2 時，管理器的位元組 +0x191c
    0x111  u32, u16, u8   隊伍描述 +0、+4、+6
    0x118  0x68   零
    0x180  u64    長度，0x118

接收者 `0x00b2e590` 把對方的 CRC 與自己的（`0x00b2e760`）相比；兩者都持有結果為 9，否則 10。

隊伍描述在 match+0x70 處一個 optional 的 match+0x98，只由對戰競技場匹配更新 `0x00ad5750` 裡的 `0x00ad9cf0` 寫入。隊伍下載任務（`0x014f7fd0`）填充它：`+0x00..+0x2f` 是結果持有者 `+0x38` 的六個 u64，`+0x30..+0x35` 是 `+0x68` 的六個位元組，`+0x36..+0x135` 來自 `+0x6e`，然後被 `v1/validate` 的簽名覆蓋。持有者取隊伍列表（`0x0150320c`）裡鍵與選中鍵相符的那條 0x158 位元組條目：

| 鍵 | 條目 |
|---|---|
| (1, team) | 一個存檔對戰隊伍：六個 u64 `box \| slot << 32`，來自 `save+0x525 + team*12 + i*2`；名字在 `save+0x4a0 + team*0x16` |
| (2, i) | 一條存下的記錄：0x87f 位元組記錄（`0x01430670`）的第 0x26..0x15b 位元組 |

簽名是 RSA-2048、PKCS#1 v1.5、SHA-256，由 `0x011aedf0(team, v, sig)` 校驗，它是 `nn::crypto::detail::BigNum::ModExp`（PLT `0x018fff50`）唯一的呼叫者。被籤的訊息是隊伍那 0x148 位元組的已存 PK8、以大端 u16 表示的金鑰版本 `v`，再是 `00 01`。主機只持有公鑰；映象裡寫著 `https://v3-lp1.vp.n.srv.nintendo.net/v1/public_key` 和 `.../v1/validate`，所以大概由任天堂的伺服器簽名。連線交換永遠走不到這項校驗。

`v1/validate`（`0x011a2a70`）傳送一個 NUL 結尾的字串（`v1/public_key` 的正文）、以大端 u16 表示的金鑰版本、主機版本 `0x2D`（盾）以大端 u16、`00 01`、一個大端計數，以及那些 0x148 位元組記錄。回覆解析器 `0x011a2870`：第 0 位元組是狀態（2：金鑰過期，重新取），第 5-6 位元組是大端計數 n（鉗到 6），n 個大端 u32，狀態為 0 時再跟一個 0x100 位元組的簽名。

比賽型別是 vtable `0x2538238`、`0x2538358`、`0x2538478` 的槽 8：1 休閒、2 排位、3 線上大賽。它們由 `0x00adcfb0(obj, mode)` 從 `StateBtlSpotTop`（`0x00b23080`）構建。塊 `+0x108` 由 `0x00adc8b0` 從 `StateBtlSpotCompTop` 寫入，取存檔塊 `0x88F6D6AE`（0x33D0 位元組；前一個鍵 `0xEEE5A3F8` 是 PKHeX 的 `KOfficialCompetition`）0x33C0 處的 u64。

### 玩家檔案

0xAEC 處的 266 位元組，也是信標在 0x1F 處的記錄（見[會話](swsh_session.md#taking-a-seat)）。`0x01111970` 從單例 `[0x2610958]`（+0x310 到 +0x564）複製它；`0x01125080` 要麼打包所有組，要麼一個都不打；按位打包的組是低位在前。`trade_payload.read_tail` 解碼它。

    0x00  16  nn::oe::GetPseudoDeviceId
    0x10  16  nn::account::GetUserId，賬號 Uid
    0x20   8  nn::account::GetNetworkServiceAccountId，或零
    0x28  24  訓練家名，UTF-16，來自 MyStatus+0xB0；終止符之後是陳舊位元組
    0x40  25  外觀，按位打包：
                第 0 位      MyStatus+0xA5（性別）!= 0
                第 1 位      由 0x0111cfec 置位；每次抓包裡都是 0
                第 2-5 位    MyStatus+0xA7，語言（3，法語）
                第 6-7 位    零
                 8 位        MyStatus+0xCC
                 17 x 10    模型 0x0111dd60 從 +0x00 處的 MyStatus 位域解出
                 2, 2, 10   那次解包的最後一組三個
    0x59  55  位置取樣，按位打包：
                 2、2 位    `a` 與 `b`，見下
                 8 位       世代：環重置時隨機（0x00eb98a8），每次重播種 +1
                 8 位       玩家物件位元組 +0x136（每次抓包裡都是 7）
                 3 x 17     在 0x5C、0x6D、0x7E，最新在前：5 位計數（每次推入 +1）；
                            3 位狀態（+0x1c8，見下）；x、y、z 三個浮點；以弧度表示的偏航角。
                            0x00ebf590 從場地物件的 +0x60（位置）與 +0x50（旋轉）每秒最多推一次
                 8 位       在 0x8F：玩家物件位元組 +0x140（每次抓包裡都是 1）
    0x90  37  活動，按位打包：一個 8 位種類（交換時為 13）、一個可選的 28 位元組部分、
              一個 24 位元組欄位、一個 0xB2 處的 u16、一個布林；只有種類與 u16 非零。那個 u16 是
              地點，即 `script/place_name.dat` 的某一行，也就是 PKHeX 的相遇地點 id
              （170 挑戰海灘）
    0xB5  37  另外兩組，每次抓包裡都是零
    0xDA  32  十六條 u16 記錄（`0x010f5060`）：Record8 的索引 6、32、0、33、17、27、34、24、
              12、3、10、35、38、7、36、37，每個鉗到 0xFFFF（PKHeX `RecordList_8`）
    0xFA   8  一個可選的 u64，每次抓包裡都是零
    0x102  8  零

接收方（0x00dd5e24）把位置存到 +0xB0，把偏航角以四元數形式存到 +0xA0。

取樣狀態（`[[0x261bd18]]` 的 `+0x1c8`，由 `0x00ebf570` 設定）在場地設定它之前是 0；為 0 時推入立即返回。狀態 1 與 2 是場地動作，3 與 4 是寶可夢露營的拜訪與會話畫面，6 是極巨團體戰匹配（`0x01466d30`）。`a` 對區域 `wr0101`、`wr0201`（鎧之孤島，抓包在 170 位置）與 `wr0301` 分別是 1、2、3，其餘為 0，來自一個 FNV-1a 64 的區域鍵；`b` 來自 vtable `0x259add8` 的槽 8 與 11。

0x90 處的活動記錄是 `0x49` 位元組，由 `0x0111b660(rec, kind)` 設定；連線交換把通訊模式設為 2（`SetMode` `0x01096d10`，見[會話](swsh_session.md#how-a-searching-sword-finds-a-partner)），經 `0x2066c40` 處的表對映為種類 13。

訓練家名出現四次（MyStatus、訓練家卡、隊伍記錄、檔案）；`pokeldn/swsh/trade_payload.rewrite` 會移動全部四處，交換畫面顯示的就是這個訓練家。空的隊伍槽是一條全零記錄，傳送時要麼是零位元組，要麼以加密常數 0 加密；兩者解密後都是零，0x810 處的數量也自洽。僅靠加密常數 0 並不能標記槽為空：HOME 3.0.0 之前的 HOME 禮物給的就是卡上的零常數（時拉比禮物，WC8 9011）[PKHeX `WC8.cs`]。`pokeldn.gen8.is_empty` 檢測的是解密後的記錄。

## PK8

與 BDSP 共用 `pokeldn/gen8.py`（PKHeX 的 `PK8` 與 `PB8` 都是 `G8PKM`）。劍傳送 0x158 的隊伍形態（`pokeldn/swsh/pokemon.py`），BDSP 傳送 0x148 的儲存形態。

    0x00  u32  加密常數，明文。給密碼與塊序播種
    0x06  u16  校驗和，明文，只覆蓋解密後的主體
    0x08       四個 80 位元組塊，經 LCG 加密，按 (EC >> 13) & 31 置換
    0x148      隊伍數值，LCG 加密且流重啟，從不置換

坑：

- 隊伍數值會重啟 LCG（`PokeCrypto.Decrypt8` 用 EC 給 `CryptArray` 播兩次種）；接著上一段流解下去會給出像等級 110 這樣看似合理的垃圾。
- `BLOCK_ORDER[sv]` 說的是“成為第 *i* 塊的是原第幾塊”：正著用，絕不要反過來。32 個 `sv` 值裡有 16 個自逆，而校驗和又忽略順序。PKHeX 的 `BlockPosition` 第 24-31 項重複了 0-7。
- 解出隊伍後可以查：暱稱與種類相符；等級與經驗相符；極限特訓位元組 0x126 與個體值字 0x8C 相符；MyStatus 的訓練家 id 與每條 PK8 相符。

## 交換訊息

`net_contents.trade.common.pokemon_trade.protocol_buffers`：

    Pokemon                  { 1 bytes   serializePokemonParam }
    PokemonTradeDataHolder   { 1 Pokemon pokemon }

一次報價在 10050 上攜帶 344 位元組的 PK8（`trade.py` 的 `pokemon_offer`）。解析 `0x010d81d0` 建一條 0x28 位元組訊息，呼叫 `ParseFromArray`（`0x0070c180`）；`MergePartialFromCodedStream`（`0x010d9ee0`）只接受 tag 0x0a。監聽者把 `[Pokemon+0x18]` 當作 libc++ 的 `std::string` 讀取，拷出 0x158。

### 接收處理器的兩處靜默丟棄

`0x010d5e40`：

    w0 = 0x006b5850(senderPointer)                            失敗為 0xfd
    if (w0 == 0xfd) { [content+0x1a4] = 1; return; }          靜默
    memcpy(stack, body, 0x158)
    subscriber = [content + 0x30 + index*8]
    if (subscriber == null || its refcount is 0) return        靜默
    ... 呼叫它，然後內容 50 的傳送 0x010d6000

內容 50 的初始化只填 `+0x30` 與 `+0x38`，所以站點索引大於 1 就直接返回；內容 40 的 `0x010dbc90` 在 `+0x38`/`+0x40` 處做同樣的閘門。主機收到 10050 會立刻用自己的回一條；沒有回來的 10050 就意味著那次報價根本沒到 `0x010d5e40`。內容 30 的槽（`0x010ce080`）只拒絕它自己的 id：一條無 owner 的報價能過盒子階段，卻在內容 50 上失敗。

### 內容 40 的訊息

`net_contents.trade.common.sync_save.protocol_buffers`：

    SyncSaveDataHolder { 1 SyncCommand syncCommand }
    SyncCommand        { 1 int32       data       }

解析 `0x010ddb20`；`0x010df6d0` 只接受 tag 0x0a，子訊息解析器 `0x010debc0` 只接受 tag 0x08。`trade.sync_command` 構建它。

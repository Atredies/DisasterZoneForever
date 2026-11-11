if DisasterZoneBoot and DisasterZoneBoot.Run("Core/DigestSync.lua", ...) then return end -- DisasterZone Core/DigestSync.lua
-- shared digest / want / give sync engine, set up per module (refactor phase 5).
local addonName, ns = ...
-- Events, Polls, Prized, RaidPlan and Strategy keep their records in one table per guild (db[bucket][guild key], a
-- table per record kind) and sync them the same way, each under its own two-letter message prefix XX:
--   the guild HELLO carries a hash over the module's digest (Sync:RegisterHelloField). A member whose hash differs
--   from the HELLO's answers once per round, after a short random delay (writers first, later when the data queue is
--   busy): a claim XXK { to } on the live prefix (the others stay quiet for that round), then the digest
--   XXD { to, h, d = { ["K:id"] = 6-hex hash } } on the data prefix. The newcomer takes the first digest of its round
--   only: it asks for what differs (XXW { w = items }, a whisper) and is sent what it lacks (XXG, a whisper). A live
--   change goes to the guild at once (XXU { k, r }); each module checks those and XXG itself.
--   Once that catch-up has settled, the newcomer sends its digest again (XXR { h, d }, the recheck: see below) until
--   nobody holds anything it lacks, so a first answer from a member who held only part of the data is not the end.
-- A digest is capped (maxItems): clients drop a bigger one whole, so the cap never goes down. Everything about the
-- wire (types, fields, their order, the caps, the hashes) is the modules' own from before this engine; it only keeps
-- one copy of the code.
-- Also here: DigestSync.RevList, the rev handshake of a list a few writers keep whole (the raid blacklist, the guest
-- book's notes), and DigestSync.BucketDigest / DiffBuckets, the per-bucket digests of the Ledger (days) and the raid
-- log (weeks).
--
-- local sync = ns.DigestSync.New({
--     module = Events, bucket = "events", kinds = { "D", "K", ... }, prefix = "EV",
--     maxItems = 1200,                 -- digest items (sent and taken)
--     maxItemLen = 91,                 -- the longest item taken in a digest or a want
--     itemPattern = "^%u:",            -- what an item must look like in a digest taken
--     helloField = "ed", helloOrder = 50,
--     delay = function() return { 0.5, 2.5 } end,   -- the answer's random delay range
--     wireKey = WireKey,               -- the module's check of a player key on the wire (a digest's / claim's "to")
--     -- optional:
--     root = function(create) end,                   -- the module's own Root (default: DB:GuildBucket + kinds)
--     items = function(root) return list end,        -- the digest's items in cap order (default: every kind's, sorted)
--     itemHash = function(root, item) end,           -- an item's short hash (default: its record's)
--     sendItem = function(root, item, target) end,   -- one item to a member (default: XXG { k, r })
--     giveSort = function(a, b) end,                 -- the order items are given in (default: sorted)
--     large = true,                                  -- XXU / XXG / XXD may be as large as a council member's
--     send = function(msg, dist, target, class) end, -- the module's own sending (default: nothing in demo mode)
--     keepHash = true,                               -- round notes keep the digest's hash (RaidPlan, Strategy)
--     waiting = function() end,                      -- true: records held back while their writer is asked (the
--                                                    -- recheck waits, see Recheck below)
--     holderHint = function(key) end,                -- true: keep that member's digests heard on GUILD (KnownHolders;
--                                                    -- relayers are kept anyway)
--     -- deletions (1.4.1, "graves"; see Graves below):
--     tombKeep = { D = 30 * DAY },                   -- per kind: how long a deletion is in the digest
--     graveKeep = 365 * DAY, maxGraves = 200,        -- then kept this long (out of the digest), this many at most
--     hidden = function(root, kind, id, rec, now) end, -- true: that item is left out of the digest too
--     -- records (Commit / StoreRecord):
--     clean = function(kind, r) end, merge = function(root, kind, rec, live) end, changed = function() end,
--     state = function() end,                        -- demo mode's data (Commit in demo mode)
--     prepare = function(kind, rec) end,             -- just before a commit's record is cleaned (has its rev)
--     demoCheck = function(state, kind, clean) end,  -- false: the demo commit is refused
--     tooBig = "text",                               -- printed when a commit would not fit one message
-- })

local DigestSync = {}
ns.DigestSync = DigestSync

local type, pairs, ipairs, tonumber = type, pairs, ipairs, tonumber
local tsort = table.sort
local floor, max, min = math.floor, math.max, math.min
local strformat = string.format

local ROUND_WINDOW = 20          -- seconds one client's round lasts (one answer, others keep quiet)
local GIVE_QUIET = 15            -- seconds without an item given to me before my catch-up counts as settled
local WANT_STALL = 300           -- ... or, with items I asked for still missing, seconds without one arriving
local ANSWER_WAIT_MAX = 60       -- seconds an answer to a HELLO waits at most for my own catch-up to settle
-- The recheck (2026-11-09, go-live load test): see "Recheck" below.
local RECHECK_FIRST = { 15, 35 } -- seconds after a catch-up was judged before its recheck (plus any time to settle)
local RECHECK_POSTPONE = { 5, 15 } -- a catch-up still running: try again after this (plus what is left of it)
local RECHECK_SETTLE_MAX = 300   -- ... but not longer than this after the recheck was due (recheck anyway)
local RECHECK_WAIT = 45          -- seconds a HELLO or recheck waits for an answer (a claim or a digest)
local RECHECK_BACKOFF = { 30, 60 } -- answered again: the next recheck after this (doubled each time)
local RECHECK_MAX_GAP = 600
local RECHECK_TRIES = 6          -- rechecks per dataset after one HELLO
local RECHECK_RANK = 12          -- an answer to a recheck waits this long divided by how many items I can give
local UNDONE_LAG = 6             -- an answer to a HELLO waits this much longer when my own copy is not confirmed
local BUSY_MAX = 45              -- an answer waits this long at most for my send queue (OnHelloDigest)
local GIVE_AGAIN = 120           -- seconds before the same version of an item goes to the same member again (SendItem)
local GAVE_MAX = 2000            -- ... remembered gives before the old ones are swept
local GM_LAG = 60                -- the GM's answer to a member's HELLO waits this much longer (OnHelloDigest) ...
local WAVE_HELLOS, WAVE_WINDOW = 8, 120   -- ... in a login wave: this many members said HELLO within this long
local PEER_KEEP = 600            -- seconds a member's digest heard on GUILD counts as what they hold (KnownHolders)
local SIZE_HEADROOM = 0.1        -- a commit leaves this much of a message free (whoever relays it adds fields)
local HASH_MAX = 8               -- longest hash taken (a digest entry, a HELLO field)

local Util = ns.Util

local Now, DemoOn = Util.Now, Util.DemoOn

local Engine = {}
Engine.__index = Engine

---------------------------------------------------------------------------
-- Records
---------------------------------------------------------------------------

-- This guild's saved table (db[bucket][guild key]) with a table for every record kind; nil while the guild is
-- unknown, or (without create) when nothing is stored yet.
function Engine:Root(create)
    if self.cfg.root then return self.cfg.root(create) end
    local r = ns.DB:GuildBucket(self.bucket, create)
    if not r then return nil end
    for _, k in ipairs(self.kinds) do
        if type(r[k]) ~= "table" then r[k] = {} end
    end
    return r
end

-- The rev for a new version of cur: now, or one past cur's when that is later (a clock behind).
function Engine.NextRev(cur)
    local prev = type(cur) == "table" and tonumber(cur.rev) or 0
    return max(Now(), prev + 1)
end

-- A new record id: prefix .. hex time .. 4 hex.
function Engine:NewId(prefix)
    self.idCounter = self.idCounter + 1
    local now = Now()
    return (prefix or "") .. strformat("%x", now)
        .. Util.Hash({ Util.PlayerKey() or "", now, self.idCounter, GetTime() }):sub(1, 4)
end

-- Higher rev wins; the same rev settles on the larger hash (every client picks the same one).
function Engine.Newer(a, b)
    if not b then return true end
    if a.rev ~= b.rev then return a.rev > b.rev end
    return Util.Hash(a) > Util.Hash(b)
end

-- (demo mode sends nothing; a module whose own data is never demo data passes its own send)
function Engine:Send(msg, dist, target, class)
    if self.cfg.send then return self.cfg.send(msg, dist, target, class) end
    if DemoOn() then return false end
    local Comm = ns.Comm
    return (Comm and Comm.Send and Comm:Send(msg, dist, target, class)) and true or false
end

local function RateLimit(key, seconds)
    local Comm = ns.Comm
    if not (Comm and Comm.RateLimit) then return true end
    return Comm:RateLimit(key, seconds)
end

-- A record from a member (live: their own change, checked against what is true now; else relayed from a store).
-- Returns stored, the clean record.
-- (sender, optional: who sent it, for the audit log; cfg.audit = the module's audit kind prefix, Core/Audit.lua)
-- (retry: a held copy tried again, Engine:RetryHeld, which keeps it when the merge still refuses it)
function Engine:StoreRecord(kind, r, live, sender, retry)
    if not self.kindSet[kind] then return false end
    local root = self:Root(true)
    if not root then return false end
    local rec = self.cfg.clean(kind, r)
    if not rec then return false end
    -- 2026-11-09 (authority holes, round 2): a relayed record names its writer (rec.by) in a field the sender controls.
    -- cfg.vouch(root, kind, rec, sender) says whether this sender may pass it on (its writer, or someone who could have
    -- written it themselves): a record whose write needs a role is otherwise refused, and comes from a writer's store.
    if not live and type(sender) == "string" and not Util.IsMe(sender) and self.cfg.vouch
        and not self.cfg.vouch(root, kind, rec, sender) then
        ns:Debug("%s: %s:%s from %s refused (relayed, not vouched for)", self.cfg.prefix or "sync", kind, tostring(rec.id),
            sender)
        -- (round 3: kept and asked for from its writer or someone who vouches for it, see Hold below)
        if self.hold then self:Hold(kind, rec, sender) end
        return false, rec
    end
    local prev = root[kind][rec.id]
    local ok = self.cfg.merge(root, kind, rec, live)
    if ok and self.cfg.audit then ns.AuditSaw(self.cfg.audit .. "." .. kind, prev, root[kind][rec.id], { via = sender }) end
    if ok and self.hold and next(self.hold.items) then self:ScheduleRetryHeld() end
    -- (a vouched copy the merge refused for now: kept to try again when the roles change, see Hold)
    if not ok and not live and not retry and self.hold and type(sender) == "string" and not Util.IsMe(sender) then
        local cur = root[kind][rec.id]
        if not (cur and not self.hold.newer(rec, cur)) then self:Hold(kind, rec, sender, true) end
    end
    return ok, rec
end

---------------------------------------------------------------------------
-- Held back (2026-11-09, authority holes round 3)
---------------------------------------------------------------------------

-- A relayed record whose sender does not vouch for it (cfg.vouch) is not taken, and not lost either: with
-- Engine:EnableHold it is kept here (memory only, HOLD_KEEP at most) and asked for (XXW, a whisper) from its writer or
-- from another online member who vouches for it (cfg.vouch with that member as the sender: someone whose store holds
-- only copies taken that way). Their answer (XXG) goes through the same checks. A vouched copy the merge refused (the
-- guild's roles not known yet after a login, a poll's answer before its poll) is kept too, without asking. Held copies
-- are tried again, and asked for from whoever may now vouch for them, when the guild's roles or roster change (someone
-- logged in) and after a record is stored. One ask per record version and member per ASK_AGAIN; a made-up record
-- nobody holds is dropped after HOLD_KEEP.
local ASK_GAP = 6                -- seconds between two asks to one member (OnWant takes one a member per 5 s)
local ASK_AGAIN = 240            -- asked again after this long (an answer may wait behind a long send queue)
local MAX_TRIES = 3              -- asks for one held copy at most
local FIRST_WAIT = 15            -- the writer is asked first only after this long (see AskHeld)
local HOLD_KEEP = 900            -- a held copy is dropped after this long

local function Count(t)
    local n = 0
    for _ in pairs(t) do n = n + 1 end
    return n
end

-- o (optional): store(kind, rec, via) (default: StoreRecord), changed() (default: cfg.changed), newer(a, b) (default:
-- Engine.Newer). Called from the module's OnInit.
function Engine:EnableHold(o)
    o = o or {}
    local eng = self
    self.hold = {
        store = o.store or function(kind, rec, via) return eng:StoreRecord(kind, rec, false, via, true) end,
        changed = o.changed or self.cfg.changed, newer = o.newer or Engine.Newer,
        items = {},              -- [item] = { kind, rec, via, at = GetTime(), ok = vouched (only the merge refused) }
        asked = {},              -- [item .. "|" .. rev .. "|" .. member] = GetTime()
        lastAsk = {},            -- [member] = GetTime()
    }
    for _, e in ipairs({ "CONFIG_UPDATED", "ACCOUNTS_UPDATED", "ROSTER_UPDATED" }) do
        ns:On(e, function() if next(eng.hold.items) then eng:ScheduleRetryHeld() end end)
    end
end

-- vouched: the sender vouches for it, only the merge refused it (tried again, never asked for).
function Engine:Hold(kind, rec, via, vouched)
    local h = self.hold
    if not h or type(rec) ~= "table" or type(rec.id) ~= "string" then return end
    local item = kind .. ":" .. rec.id
    local cur = h.items[item]
    if cur and not h.newer(rec, cur.rec) and not (vouched and not cur.ok) then return end
    if not cur and Count(h.items) >= self.maxItems then return end
    h.items[item] = { kind = kind, rec = rec, via = via, at = GetTime(), ok = vouched and true or nil }
    if not vouched then self:ScheduleAskHeld(2) end
end

-- Am I still waiting for a vouched copy of a record someone passed on (held less than HOLD_QUIET ago)? My store is
-- then likely incomplete (a catch-up from a plain member, the vouched copies still on their way): I leave answering a
-- newcomer's HELLO to the others (OnHelloDigest), or the newcomer would sync with a store that lacks them.
local HOLD_QUIET = 120
function Engine:Waiting()
    local h = self.hold
    if not h or not next(h.items) then return false end
    local now = GetTime()
    for _, p in pairs(h.items) do
        if not p.ok and now - p.at < HOLD_QUIET then return true end
    end
    return false
end

-- The relayers online other than me and `except` (cfg.relayer; none without Hold).
function Engine:OnlineRelayers(except)
    local relayer = self.hold and self.cfg.relayer
    local list = {}
    if not relayer then return list end
    local G = ns.Guild
    for _, m in ipairs(G and G.GetOnlineMembers and G:GetOnlineMembers() or {}) do
        if not Util.IsMe(m) and m ~= except and relayer(m) then list[#list + 1] = m end
    end
    return list
end

-- Is a login wave on? (WAVE_HELLOS members said HELLO within WAVE_WINDOW; NoteHello from OnHelloDigest)
local helloAt = {}
local function NoteHello(sender) helloAt[sender] = GetTime() end
local function InWave()
    local now, n = GetTime(), 0
    for k, t in pairs(helloAt) do
        if now - t > WAVE_WINDOW then helloAt[k] = nil else n = n + 1 end
    end
    return n >= WAVE_HELLOS
end

function Engine:AmGM()
    local G = ns.Guild
    return G ~= nil and G.IsGM ~= nil and G:IsGM(Util.PlayerKey()) and true or false
end

-- (round 4) What other members hold, as their last digest on GUILD said (an answer XXD, a recheck XXR: every member
-- hears them). Only a hint for whom to ask (KnownHolders): what they send goes through the same checks.
-- Kept only for the members ever asked that way: relayers (cfg.relayer, with Hold), or cfg.holderHint(key) (RaidPlan:
-- the raid planners), so the memory stays a few digests.
function Engine:NotePeerDigest(member, d)
    if type(member) ~= "string" or Util.IsMe(member) or type(d) ~= "table" then return end
    local relayer = self.hold and self.cfg.relayer
    local hint = self.cfg.holderHint
    if not ((relayer and relayer(member)) or (hint and hint(member))) then return end
    local now = GetTime()
    for m, p in pairs(self.peerDigest) do
        if now - p.at > PEER_KEEP then self.peerDigest[m] = nil end
    end
    self.peerDigest[member] = { d = d, at = now }
end

-- Of the members in list, those not known to lack any of items: their last digest (NotePeerDigest) held every one, or
-- none of theirs was heard. When every one is known to lack some, those that held the most; when that is none, list.
-- (Whoever holds a record may give it: the receiver's checks decide whether it is taken.) known: only those whose
-- digest was heard count (nil when none of them is known to hold them all).
function Engine:KnownHolders(list, items, known)
    local ok, best, bestN = {}, {}, 0
    local now = GetTime()
    for _, m in ipairs(list) do
        local p = self.peerDigest[m]
        if not p or now - p.at > PEER_KEEP then
            if not known then ok[#ok + 1] = m end
        else
            local n = 0
            for _, item in ipairs(items) do
                if p.d[item] ~= nil then n = n + 1 end
            end
            if n == #items then
                ok[#ok + 1] = m
            elseif n > bestN then
                best, bestN = { m }, n
            elseif n == bestN and n > 0 then
                best[#best + 1] = m
            end
        end
    end
    if #ok > 0 then return ok end
    if known then return nil end
    if bestN == 0 then return list end
    return best
end

-- One of list, picked by my name (so a login wave's newcomers spread over them).
local function PickByName(list, salt)
    return list[1 + Util.Adler32((Util.PlayerKey() or "") .. (salt or "")) % #list]
end

-- Whom to ask for what a digest from `sender` showed I lack (OnDigest). A member who passes on only what they wrote
-- themselves would have most of it held back (and fetched again): with cfg.relayer(key) (may that member pass on any
-- of the module's records), such a digest's items are asked from a relayer online instead, picked by my name.
-- (round 4: a relayer whose last digest showed it holds the items, when one is known: in a login wave a relayer picked
-- blindly often still lacked them itself, and the want only came back by the fallback)
-- The GM is asked only when nobody else on the list can be: the GM writes most records, so in a login wave every
-- newcomer lacks them and the GM's send queue is the longest (go-live load test: the GM's gives alone took longer
-- than the 20-minute limit under the strict send limit, while the officers, who vouch for the same records, idled).
local function SpareGM(list)
    local G = ns.Guild
    if #list < 2 or not (G and G.IsGM) then return list end
    local out = {}
    for _, m in ipairs(list) do
        if not G:IsGM(m) then out[#out + 1] = m end
    end
    return #out > 0 and out or list
end

function Engine:WantFrom(sender, want, theirs)
    local relayer = self.hold and self.cfg.relayer
    if not relayer then return sender end
    -- (a relayer myself: the GM is not spared, the other relayers serve the guild with what I hold once I have it)
    local amRelayer = relayer(Util.PlayerKey())
    if relayer(sender) then
        -- (the GM answered: another relayer whose last digest held every item as the GM's does is asked instead)
        local G = ns.Guild
        if amRelayer or not (want and theirs and G and G.IsGM and G:IsGM(sender)) then return sender end
        local now, list = GetTime(), {}
        for _, m in ipairs(self:OnlineRelayers(sender)) do
            local p = self.peerDigest[m]
            local all = p ~= nil and now - p.at <= PEER_KEEP
            for _, item in ipairs(all and want or {}) do
                if p.d[item] ~= theirs[item] then all = false break end
            end
            if all then list[#list + 1] = m end
        end
        return #list > 0 and PickByName(list) or sender
    end
    local list = self:OnlineRelayers(sender)
    if #list == 0 then return sender end
    if want then list = self:KnownHolders(list, want) end
    return PickByName(amRelayer and list or SpareGM(list))
end

-- Asks for the items a digest from `sender` (theirs) showed I lack: from a relayer (WantFrom) when the sender is none;
-- what has not come WANT_FALLBACK later (the relayer may lack it too, in the same login wave) from the sender after all
-- (their copies are then held back and asked for, Hold).
local WANT_FALLBACK = 150         -- (a busy relayer's answer can wait a minute or two behind its queue)
function Engine:SendWant(sender, want, theirs)
    local from = self:WantFrom(sender, want, theirs)
    self:Send({ t = self.T.W, w = want }, "WHISPER", from, "ctrl")
    if from == sender then return end
    -- (round 4: what that relayer has not sent by the fallback it likely lacks: AskHeld asks someone else for it)
    local now = GetTime()
    for item, w in pairs(self.wantedFrom) do
        if now - w.at > ASK_AGAIN then self.wantedFrom[item] = nil end
    end
    for _, item in ipairs(want) do self.wantedFrom[item] = { m = from, at = now } end
    Util.After(WANT_FALLBACK, function()
        local mine = self.module:GetDigest()
        local rest = {}
        for _, item in ipairs(want) do
            if mine[item] ~= theirs[item] and not (self.hold and self.hold.items[item]) then rest[#rest + 1] = item end
        end
        if #rest > 0 then self:Send({ t = self.T.W, w = rest }, "WHISPER", sender, "ctrl") end
    end)
end

-- Is this record held back? (tests, debugging)
function Engine:IsHeld(kind, id)
    return self.hold ~= nil and self.hold.items[kind .. ":" .. tostring(id)] ~= nil
end

function Engine:ScheduleRetryHeld()
    Util.Debounce("dsync-retry-" .. (self.cfg.prefix or "?"), 1, function() self:RetryHeld() end)
end

function Engine:ScheduleAskHeld(delay)
    Util.Debounce("dsync-ask-" .. (self.cfg.prefix or "?"), delay or 2, function() self:AskHeld() end)
end

-- The held records again: one I now hold as new or newer, or held too long, is dropped; one someone now vouches for
-- is stored (kept, if the merge still refuses it).
function Engine:RetryHeld()
    local h = self.hold
    if not h or not next(h.items) then return false end
    local root = self:Root(false)
    if not root then return false end
    local changed, now = false, GetTime()
    for item, p in pairs(h.items) do
        local cur = root[p.kind] and root[p.kind][p.rec.id]
        if (cur and not h.newer(p.rec, cur)) or now - p.at > HOLD_KEEP then
            h.items[item] = nil
        elseif p.ok or self.cfg.vouch(root, p.kind, p.rec, p.via) then
            h.items[item] = nil
            if h.store(p.kind, p.rec, p.via) then
                changed = true
            elseif not h.items[item] then
                p.ok = true
                h.items[item] = p
            end
        end
    end
    if changed and h.changed then h.changed() end
    if next(h.items) then self:ScheduleAskHeld(1) end
    return changed
end

-- Asks for the held records, each from one online member who vouches for it (never the member who passed it on), one
-- message per member. First a role holder who vouches for every such record (a reviewer, an asker: one message for all
-- of them), picked by my name, so that after a login wave the newcomers' asks spread over the role holders instead of
-- all going to the writer (often the GM) or to every member who wrote a sign-up; else the writer. A role holder may
-- not hold it yet (in the same login wave): it is asked again after ASK_AGAIN, from the writer first when online.
function Engine:AskHeld()
    local h = self.hold
    if not h or not next(h.items) then return end
    local root = self:Root(false)
    local G = ns.Guild
    if not (root and G and G.GetOnlineMembers) then return end
    local online = G:GetOnlineMembers()
    local now = GetTime()
    local lists, wait, again = {}, nil, false
    for item, p in pairs(h.items) do
        if not p.ok and p.askedAt and now - p.askedAt < ASK_AGAIN then
            again = true             -- (its answer may still be on its way)
        elseif not p.ok then
            local rev = tostring(p.rec.rev)
            local cands, writer, recent = {}, nil, false
            local wf = self.wantedFrom[item]
            for _, m in ipairs(online) do
                local at = h.asked[item .. "|" .. rev .. "|" .. m]
                if wf and wf.m == m and not (at and at > wf.at) then at = wf.at end   -- (asked by SendWant)
                local isWriter = m == p.rec.by or (G.SameAccount and G:SameAccount(m, p.rec.by))
                if Util.IsMe(m) or m == p.via then
                    -- (never)
                elseif at and now - at < ASK_AGAIN then
                    recent = true
                elseif isWriter then
                    writer = writer or m
                elseif self.cfg.vouch(root, p.kind, p.rec, m) then
                    cands[#cands + 1] = m
                end
            end
            p.tries = p.tries or 0
            local pick
            if p.tries >= MAX_TRIES then
                -- (asked enough: kept until HOLD_KEEP, for a member who logs in to vouch for it)
            elseif writer and #cands == 0 and p.tries == 0 and now - p.at < FIRST_WAIT then
                -- (just after a login the guild's roles may not be known yet: a role holder is asked rather than the
                -- writer, who after a login wave would otherwise be asked by every newcomer)
                again, wait = true, max(wait or 0, FIRST_WAIT - (now - p.at))
            elseif writer and (p.tries > 0 or #cands == 0) then
                pick = writer
                -- (round 4: asked again, a role holder whose last digest holds this very version spares the writer,
                -- often the GM with the longest queue of a login wave)
                if p.tries > 0 and #cands > 0 and not self.cfg.itemHash then
                    local h, now2, list = Util.Hash(p.rec):sub(1, 6), GetTime(), {}
                    for _, m in ipairs(cands) do
                        local pd = self.peerDigest[m]
                        if pd and now2 - pd.at <= PEER_KEEP and pd.d[item] == h then list[#list + 1] = m end
                    end
                    if #list > 0 then pick = PickByName(list, p.tries) end
                end
            elseif #cands > 0 then
                pick = PickByName(self:KnownHolders(cands, { item }), p.tries)
            elseif recent then
                again = true
            end
            if pick then
                local gap = ASK_GAP - (now - (h.lastAsk[pick] or -1000))
                if gap > 0 and not lists[pick] then
                    wait = max(wait or 0, gap)
                else
                    h.asked[item .. "|" .. rev .. "|" .. pick] = now
                    p.tries, p.askedAt = p.tries + 1, now
                    again = true
                    lists[pick] = lists[pick] or {}
                    local l = lists[pick]
                    if #l < self.maxItems then l[#l + 1] = item end
                end
            end
        end
    end
    for m, list in pairs(lists) do
        h.lastAsk[m] = now
        if self.cfg.giveSort then tsort(list, self.cfg.giveSort) else tsort(list) end
        self:Send({ t = self.T.W, w = list }, "WHISPER", m, "ctrl")
    end
    if wait then self:ScheduleAskHeld(wait + 0.1) end
    -- (still held after ASK_AGAIN: asked again; RetryHeld drops what came or is held too long)
    if again then
        Util.Debounce("dsync-again-" .. (self.cfg.prefix or "?"), ASK_AGAIN + 1, function()
            self:RetryHeld()
            self:AskHeld()
        end)
    end
end

-- My own change: stored (merged like anyone's), then sent to the guild (XXU). Demo mode changes its own data only.
-- Returns ok, the clean record.
function Engine:Commit(kind, rec)
    local cfg = self.cfg
    rec.by = rec.by or Util.PlayerKey()
    if DemoOn() then
        local st = cfg.state()
        rec.rev = self.NextRev(st[kind][rec.id])
        if cfg.prepare then cfg.prepare(kind, rec) end
        local clean = cfg.clean(kind, rec)
        if not clean then return false end
        if cfg.demoCheck and not cfg.demoCheck(st, kind, clean) then return false end
        st[kind][rec.id] = clean
        cfg.changed()
        return true, clean
    end
    local root = self:Root(true)
    if not root then return false end      -- (the guild key is not known yet: GetGuildInfo lags after a login)
    rec.rev = self.NextRev(root[kind][rec.id])
    if cfg.prepare then cfg.prepare(kind, rec) end
    local clean = cfg.clean(kind, rec)
    if not clean then return false end
    local Comm = ns.Comm
    if Comm and Comm.Fits and not Comm:Fits({ t = self.T.U, k = kind, r = clean }, SIZE_HEADROOM) then
        ns:Print(cfg.tooBig)
        return false
    end
    local prev = root[kind][clean.id]
    if not cfg.merge(root, kind, clean, true) then return false end
    if cfg.audit then ns.AuditSaw(cfg.audit .. "." .. kind, prev, root[kind][clean.id], { mine = true }) end
    self:Send({ t = self.T.U, k = kind, r = clean }, "GUILD", nil, "data")
    cfg.changed()
    return true, clean
end

---------------------------------------------------------------------------
-- Digest
---------------------------------------------------------------------------

local function DefaultItems(self, root)
    local items = {}
    for _, kind in ipairs(self.kinds) do
        for id in pairs(root[kind]) do items[#items + 1] = kind .. ":" .. id end
    end
    tsort(items)
    return items
end

local function DefaultItemHash(root, item)
    local kind, id = item:match("^(%u):(.+)$")
    local rec = kind and root[kind] and root[kind][id]
    return rec and Util.Hash(rec):sub(1, 6) or nil
end

-- { [item] = short hash } of everything I hold for my guild, the first maxItems items (clients drop a bigger digest).
function Engine:GetDigest()
    local out = {}
    local root = self:Root(false)
    if not root then return out end
    local items = self.cfg.items and self.cfg.items(root) or DefaultItems(self, root)
    local itemHash = self.cfg.itemHash or DefaultItemHash
    local graves = self.cfg.tombKeep ~= nil
    local now = graves and Now()
    local n = 0
    for _, item in ipairs(items) do
        local h = not (graves and self:Hidden(root, item, now)) and itemHash(root, item) or nil
        if h then
            n = n + 1
            if n > self.maxItems then break end
            out[item] = h
        end
    end
    return out
end

-- One hash over the digest ("0" = I hold nothing). Sent in the HELLO.
function Engine:GetDigestHash()
    local d = self.module:GetDigest()
    local list = {}
    for item, h in pairs(d) do list[#list + 1] = item .. "=" .. h end
    if #list == 0 then return "0" end
    tsort(list)
    return Util.Hash(list)
end

-- One item to a member (XXG, a whisper).
-- (2026-11-09, round 4: the same version of an item is not queued for one member again while its copy still waits in
-- my send queue (GIVE_AGAIN at most). In a login wave a newcomer asked several members for the same items (a want, a
-- recheck's want, a held copy asked for) and the GM, whose queue was long, sent each answer minutes later, long after
-- the item had come from someone else; under the strict send limit those copies took minutes of the GM's sending.
-- Once the copy left, the member may ask again and gets it again: it may have refused it then.)
function Engine:SendItem(root, item, target)
    local Comm = ns.Comm
    local itemHash = self.cfg.itemHash or DefaultItemHash
    local h = Comm and Comm.Drained and itemHash(root, item)
    local key, now
    if h then
        key, now = target .. "|" .. item .. "|" .. h, GetTime()
        local g = self.gaveTo[key]
        if g and now - g.at < GIVE_AGAIN and Comm:Drained("data") < g.mark then return end
        if not g then
            self.gaveN = self.gaveN + 1
            if self.gaveN > GAVE_MAX then
                for k, e in pairs(self.gaveTo) do
                    if now - e.at >= GIVE_AGAIN then self.gaveTo[k], self.gaveN = nil, self.gaveN - 1 end
                end
            end
        end
    end
    if self.cfg.sendItem then
        self.cfg.sendItem(root, item, target)
    else
        local kind, id = item:match("^(%u):(.+)$")
        if kind and self.kindSet[kind] and root[kind][id] then
            self:Send({ t = self.T.G, k = kind, r = root[kind][id] }, "WHISPER", target, "data")
        end
    end
    -- (it has left once as many bytes of the data queue drained as were in it, or had left, just after it was queued)
    if key then self.gaveTo[key] = { at = now, mark = Comm:Drained("data") + Comm:Backlog("data") } end
end

function Engine:CleanDigest(d)
    if type(d) ~= "table" then return nil end
    local out, n = {}, 0
    for item, h in pairs(d) do
        n = n + 1
        if n > self.maxItems then return nil end
        if type(item) ~= "string" or #item > self.maxItemLen or not item:find(self.itemPattern) then return nil end
        if type(h) ~= "string" or #h > HASH_MAX then return nil end
        out[item] = h
    end
    return out
end

---------------------------------------------------------------------------
-- Graves (1.4.1): deletions outlive their time in the digest
---------------------------------------------------------------------------

-- A deletion (a compact tombstone, del = true) is in the digest for cfg.tombKeep[kind] after it was made, as before
-- 1.4.1 (clients before it prune it then, so the digest hashes stay equal). After that it stays in the same kind
-- table as a grave, out of the digest, until cfg.graveKeep (cfg.maxGraves at most, the oldest dropped first): a live
-- copy from a member who was away all that time is refused by the module's merge (a deletion wins), and the sender
-- gets the deletion back (XXG, ReturnGrave); a digest that lists such a copy gets it too (OnDigest). Nothing new is
-- saved or sent: the same records in the same tables, the same messages.

-- How long a deletion of that kind is in the digest (nil: the kind keeps no graves).
function Engine:TombKeep(kind)
    local tk = self.cfg.tombKeep
    if type(tk) == "table" then return tk[kind] end
    return tk
end

-- Is rec (of that kind) a grave: a deletion past its time in the digest?
function Engine:IsGrave(kind, rec, now)
    local tk = self:TombKeep(kind)
    return tk ~= nil and type(rec) == "table" and rec.del and (tonumber(rec.rev) or 0) < (now or Now()) - tk or false
end

-- Is that digest item left out of the digest? Returns hidden, grave (it is one of my graves).
function Engine:Hidden(root, item, now)
    local kind, id = item:match("^(%u):(.+)$")
    if not kind then return false, false end
    local rec = root[kind] and root[kind][id]
    if self:IsGrave(kind, rec, now) then return true, true end
    local hook = self.cfg.hidden
    return (hook and hook(root, kind, id, rec, now or Now())) and true or false, false
end

-- Do I hold a grave? (A store of graves only hashes "0", yet still answers a HELLO: see OnHelloDigest.)
function Engine:HasGraves()
    if self.cfg.tombKeep == nil then return false end
    local root = self:Root(false)
    if not root then return false end
    local now = Now()
    for _, kind in ipairs(self.kinds) do
        if self:TombKeep(kind) and type(root[kind]) == "table" then
            for _, rec in pairs(root[kind]) do
                if self:IsGrave(kind, rec, now) then return true end
            end
        end
    end
    return false
end

-- Drops the graves past cfg.graveKeep (never before tombKeep), then the oldest past cfg.maxGraves. For the module's
-- Prune; returns true when something was dropped.
function Engine:PruneGraves(root, now)
    now = now or Now()
    local graves, changed = {}, false
    for _, kind in ipairs(self.kinds) do
        local tk = self:TombKeep(kind)
        local t = tk and root[kind]
        if t then
            local keep = max(tk, self.cfg.graveKeep or 0)
            for id, rec in pairs(t) do
                if rec.del and (tonumber(rec.rev) or 0) < now - keep then
                    t[id] = nil
                    changed = true
                elseif self:IsGrave(kind, rec, now) then
                    graves[#graves + 1] = { kind = kind, id = id, rev = tonumber(rec.rev) or 0 }
                end
            end
        end
    end
    local cap = self.cfg.maxGraves
    if cap and #graves > cap then
        tsort(graves, function(a, b)
            if a.rev ~= b.rev then return a.rev < b.rev end
            if a.kind ~= b.kind then return a.kind < b.kind end
            return a.id < b.id
        end)
        for i = 1, #graves - cap do root[graves[i].kind][graves[i].id] = nil end
        changed = true
    end
    return changed
end

-- A record from sender (r, as sent) was refused: when it is a live copy of one of my graves, the deletion goes back
-- to them (XXG, a whisper), once a minute per member and record.
function Engine:ReturnGrave(kind, r, sender)
    if type(r) ~= "table" or r.del or type(r.id) ~= "string" or type(sender) ~= "string" or Util.IsMe(sender) then
        return
    end
    local root = self:Root(false)
    local rec = root and root[kind] and root[kind][r.id]
    if not self:IsGrave(kind, rec) then return end
    if not RateLimit(self.T.G .. "g:" .. sender .. ":" .. kind .. r.id, 60) then return end
    self:Send({ t = self.T.G, k = kind, r = rec }, "WHISPER", sender, "data")
end

-- StoreRecord for a record sender sent me (XXU / XXG); a refused copy of a grave gets the deletion back.
function Engine:StoreFrom(sender, kind, r, live)
    local ok, rec = self:StoreRecord(kind, r, live, sender)
    if not ok then self:ReturnGrave(kind, r, sender) end
    return ok, rec
end

---------------------------------------------------------------------------
-- Handlers
---------------------------------------------------------------------------

-- XXW { w = { item, ... } }: the items a member wants from me.
function Engine:OnWant(sender, msg, dist)
    if dist ~= "WHISPER" or type(msg.w) ~= "table" or not RateLimit(self.T.W .. ":" .. sender, 5) then return end
    local root = self:Root(false)
    if not root then return end
    local items = {}
    for i = 1, self.maxItems do
        local item = msg.w[i]
        if item == nil then break end
        if type(item) == "string" and #item <= self.maxItemLen then items[#items + 1] = item end
    end
    -- (in the module's give order: a record before the ones that refer to it, whatever order they were asked in)
    if self.cfg.giveSort then tsort(items, self.cfg.giveSort) end
    for _, item in ipairs(items) do self:SendItem(root, item, sender) end
end

-- XXD { to, h, d }: an answer to someone's HELLO. Mine: sync with the responder (the first answer of my round only).
-- Someone else's: remember it, so I don't answer the same round.
function Engine:OnDigest(sender, msg, dist)
    if dist ~= "GUILD" then return end
    local to = self.cfg.wireKey(msg.to)
    if not to then return end
    if not Util.IsMe(to) then
        if not self.keepHash then
            self.roundSeen[to] = { at = GetTime() }
        elseif type(msg.h) == "string" then
            self.roundSeen[to] = { h = msg.h, at = GetTime() }
        end
        self:NotePeerDigest(sender, self:CleanDigest(msg.d))
        return
    end
    local theirs = self:CleanDigest(msg.d)
    if not theirs then return end
    self:NotePeerDigest(sender, theirs)
    -- (round 4: a later digest of the same round is not ignored when it lists items I lack that the round has not
    -- asked for yet: in a login wave the first answer was often a member holding a few records, and the GM's full
    -- digest a moment later was dropped, leaving the rest to the recheck minutes later. Only those items are asked
    -- for; nothing is given back.)
    local late = GetTime() - self.answeredAt < ROUND_WINDOW
    if not late then
        self.answeredAt = GetTime()
        self.done = false   -- (a catch-up: my copy is not confirmed now; its recheck follows)
        self:NoteRecheckAnswer(true)
        self.roundWanted = {}
    end
    local root = self:Root(true)
    if not root then return end
    local mine = self.module:GetDigest()
    local want, give = {}, {}
    local graves = self.cfg.tombKeep ~= nil
    local now = graves and Now()
    local itemHash = self.cfg.itemHash or DefaultItemHash
    for item, h in pairs(theirs) do
        if mine[item] ~= h then
            -- (1.4.1) a record I hold as a grave: they get the deletion, and I don't ask for their copy
            local hidden, grave = false, false
            if graves then hidden, grave = self:Hidden(root, item, now) end
            -- (round 4: a held copy already asked for from a relayer is on its way: not asked for twice)
            local held = self.hold and self.hold.items[item]
            if held and not held.ok and held.askedAt and GetTime() - held.askedAt < ASK_AGAIN then hidden = true end
            if late and self.roundWanted[item] then hidden = true end
            if not hidden then
                want[#want + 1] = item
            elseif grave and itemHash(root, item) ~= h then
                give[#give + 1] = item
            end
        end
    end
    for item, h in pairs(late and {} or mine) do
        if theirs[item] ~= h then give[#give + 1] = item end
    end
    if late then
        give = {}
        if #want == 0 then return end
    end
    if self.cfg.giveSort then
        tsort(want, self.cfg.giveSort)
        tsort(give, self.cfg.giveSort)
    else
        tsort(want)
        tsort(give)
    end
    self.wantLeft = (late and self.wantLeft or 0) + #want   -- (CatchUpLeft: one give a wanted item)
    for _, item in ipairs(want) do self.roundWanted[item] = true end
    if #want > 0 then self:SendWant(sender, want, theirs) end
    for _, item in ipairs(give) do self:SendItem(root, item, sender) end
end

-- XXK { to }: someone is about to answer that client's HELLO with a digest.
function Engine:OnClaim(sender, msg, dist)
    if dist ~= "GUILD" then return end
    local to = self.cfg.wireKey(msg.to)
    if not to then return end
    if Util.IsMe(to) then
        self:NoteRecheckAnswer()   -- (my recheck is answered: the digest follows in the bulk queue)
        return
    end
    self.roundSeen[to] = self.keepHash and { h = "", at = GetTime() } or { at = GetTime() }
end

-- Sync calls this for every HELLO on GUILD (hash = the sender's digest hash; nil from older clients). offer (a
-- recheck, OnRecheck): how many items I hold that the sender lacks; the more, the sooner I answer.
function Engine:OnHelloDigest(sender, hash, offer)
    if type(hash) ~= "string" or #hash > HASH_MAX or type(sender) ~= "string" then return end
    if not offer then NoteHello(sender) end
    local M = self.module
    local mine = M:GetDigestHash()
    -- (1.4.1: graves only, an empty digest still answers: a member back from a long break gives me its copies, and
    -- gets the deletions back)
    if hash == mine or (mine == "0" and not self:HasGraves()) then return end
    if self:Waiting() then return end    -- (round 3: my store is still incomplete, see Engine:Waiting)
    if not RateLimit(self.T.D .. "h:" .. sender, ROUND_WINDOW) then return end
    local delay = self.cfg.delay()
    -- With item data still waiting in my queue the digest (and what the newcomer then asks for) would wait behind
    -- it: answer after the members whose queue is empty had their turn (they serve the newcomer faster).
    local Comm = ns.Comm
    local queued = Comm and Comm.Backlog and Comm:Backlog("data") or 0
    -- (round 4: up to BUSY_MAX, about how long the queue takes to drain, so in a login wave the answers spread over
    -- the members who can send soonest instead of all going to the GM, whose queue then held the whole guild's data)
    -- (a relayer asking (cfg.relayer, Hold): the old cap of 12 s; once it holds the records it serves the others)
    local relayerAsks = self.hold and self.cfg.relayer and self.cfg.relayer(sender)
    local busy = queued > 0 and min(relayerAsks and 12 or BUSY_MAX, 6 + queued / 240) or 0
    -- Still catching up myself (my own round was answered moments ago, or its items are still coming in): what I hold
    -- is incomplete, so I only answer once that settled, if nobody else did.
    busy = max(busy, min(self:CatchUpLeft(), ANSWER_WAIT_MAX))
    -- A recheck goes to the member who can give the most, a HELLO first to a member whose copy is confirmed (done)
    -- (go-live load test: in a login wave the first answer often came from a member holding part of the data, and the
    -- newcomer took only that).
    if offer then
        busy = busy + RECHECK_RANK / max(1, offer)
    elseif not self.done then
        busy = busy + UNDONE_LAG
    end
    -- (round 4: the GM answers a member's HELLO last: in a login wave the GM was the only member whose copy was
    -- confirmed, answered every HELLO first and then served the whole guild from one send queue, where the officers'
    -- own catch-up (they serve the records only a role holder may pass on) waited its turn among 40 whispers)
    -- Only in a login wave (WAVE_HELLOS members said HELLO within WAVE_WINDOW): otherwise the GM's answer is the one
    -- that serves a newcomer best.
    if not offer and not relayerAsks and self:AmGM() and InWave() then busy = busy + GM_LAG end
    local asked = GetTime()
    local function Answer()
        local h = M:GetDigestHash()
        local seen = self.roundSeen[sender]
        -- Somebody answered this round already (whatever their hash): the newcomer syncs with the first answer only
        -- (answeredAt in OnDigest), so one more is noise.
        if (h == "0" and not self:HasGraves())
            or (seen and (GetTime() - seen.at < ROUND_WINDOW or seen.at >= asked)) then return end
        -- my own catch-up began meanwhile, or is still running: wait for it (ANSWER_WAIT_MAX at most)
        local left = self:CatchUpLeft()
        if left > 0 and GetTime() - asked < ANSWER_WAIT_MAX then
            return Util.RandomDelay(left + 1, left + 4, Answer)
        end
        if h == hash then return end   -- (meanwhile my copy became theirs)
        self.roundSeen[sender] = self.keepHash and { h = h, at = GetTime() } or { at = GetTime() }
        -- The digest waits in the bulk queue behind item data; this short claim on the (mostly idle) live prefix tells
        -- the others right away that the round is answered (older clients have no handler for it and ignore it).
        self:Send({ t = self.T.K, to = sender }, "GUILD", nil, "live")
        self:Send({ t = self.T.D, to = sender, h = h, d = M:GetDigest() }, "GUILD", nil, "data")
    end
    Util.RandomDelay(delay[1] + busy, delay[2] + busy, Answer)
end

-- Seconds until my own catch-up has settled (0: settled): my round was answered under ROUND_WINDOW ago, or an item
-- was given to me under GIVE_QUIET ago.
-- Items I asked for and have not had yet keep it running, until none came for WANT_STALL (a responder gone, a record
-- refused or merged away).
function Engine:CatchUpLeft()
    local now = GetTime()
    local stall = self.wantLeft > 0 and WANT_STALL - (now - max(self.answeredAt, self.givenAt)) or 0
    return max(0, ROUND_WINDOW - (now - self.answeredAt), GIVE_QUIET - (now - self.givenAt), stall)
end

---------------------------------------------------------------------------
-- Recheck (2026-11-09, go-live load test)
---------------------------------------------------------------------------

-- A newcomer syncs with the first member who answers its HELLO. In a login wave that is often a member who holds
-- only part of the data itself (live changes it heard after its own login, a catch-up from another partial member),
-- and nothing started a second round before the next login: 32 of 40 members lacked events after the wave.
-- So a catch-up of mine (a digest for me) is followed by a recheck once it has settled (CatchUpLeft): XXR { h, d } on
-- GUILD, my digest hash and digest again (an XXD without a "to"). A member who holds items I lack (or hold otherwise)
-- answers it as it answers a HELLO (OnHelloDigest: one answer per round, a claim keeps the others quiet, the exchange
-- goes both ways), the member with the most of them first (RECHECK_RANK), members still catching up only once they
-- settled. A member with nothing for me stays quiet (what I hold that it lacks reaches it with its own recheck). A
-- HELLO or recheck that draws no answer within RECHECK_WAIT: nobody online holds anything I lack, that dataset is
-- done. One that is answered is checked again after a backoff (RECHECK_FIRST, then RECHECK_BACKOFF doubling),
-- RECHECK_TRIES times at most per HELLO. In a converged guild nothing changes on the wire: nobody answers a HELLO, so
-- nobody rechecks. Who may write what does not change either: the records come through the same digest, want and give
-- messages and their checks. Older clients ignore XXR.
local engines = {}               -- every engine with a HELLO field, in registration order
local recheckGen = 0             -- a new HELLO restarts the rechecks (the timers of the old ones see a newer gen)
local fireAt                     -- GetTime() the next recheck is due (nil: none scheduled)
local armedAt                    -- GetTime() of my last HELLO

local FireRecheck

-- The next recheck in lo..hi seconds (unless one is due sooner).
local function ScheduleRecheck(lo, hi)
    local gen, at = recheckGen, GetTime() + lo + math.random() * (hi - lo)
    if fireAt and fireAt <= at then return end
    fireAt = at
    Util.After(at - GetTime(), function()
        if gen ~= recheckGen or fireAt ~= at then return end
        fireAt = nil
        FireRecheck(gen)
    end)
end

-- That dataset is due for a recheck (a catch-up of mine happened): after RECHECK_FIRST, then a doubling backoff.
function Engine:RecheckDue()
    if self.due or self.check or self.rechecks >= RECHECK_TRIES then return end
    self.due, self.dueAt = true, GetTime()
    if self.rechecks == 0 then return ScheduleRecheck(RECHECK_FIRST[1], RECHECK_FIRST[2]) end
    local f = 2 ^ (self.rechecks - 1)
    ScheduleRecheck(min(RECHECK_BACKOFF[1] * f, RECHECK_MAX_GAP), min(RECHECK_BACKOFF[2] * f, RECHECK_MAX_GAP))
end

-- A claim or digest for me arrived (digest: a catch-up of mine). While a HELLO or recheck of mine waits, it was
-- answered (JudgeRecheck follows up); otherwise a digest makes the dataset due.
function Engine:NoteRecheckAnswer(digest)
    local c = self.check
    if c and GetTime() - c.sentAt < RECHECK_WAIT + ROUND_WINDOW then
        c.answered = true
    elseif digest then
        self.check = nil
        self:RecheckDue()
    end
end

-- RECHECK_WAIT after a HELLO or recheck (sent at sentAt): unanswered, the dataset is done (nobody online holds
-- anything I lack; my copy is confirmed); answered, it is due again.
function Engine:JudgeRecheck(gen, sentAt)
    local c = self.check
    if gen ~= recheckGen or not c or c.sentAt ~= sentAt then return end
    self.check = nil
    if c.answered then
        self:RecheckDue()
    elseif not self.due then
        self.done = true
    end
end

local function JudgeLater(e, gen, sentAt)
    Util.After(RECHECK_WAIT, function() e:JudgeRecheck(gen, sentAt) end)
end

-- Sends each due dataset's recheck once its catch-up has settled (RECHECK_SETTLE_MAX at most). (Even after a catch-up
-- from a member whose own copy was confirmed: under the strict send limit an answer can come after RECHECK_WAIT, so a
-- "confirmed" copy may still lack something.)
FireRecheck = function(gen)
    local now = GetTime()
    local later
    for _, e in ipairs(engines) do
        if e.due then
            -- (a catch-up still running, or records held back while their writer is asked (cfg.waiting): what I hold
            -- is not final yet, and a recheck now would only ask for items on their way)
            -- (round 4: held relays being fetched from a relayer count too, Engine:Waiting; the recheck would only
            -- draw a second copy of them)
            local held = e:Waiting() or (e.cfg.waiting and e.cfg.waiting())
            local wait = max(e:CatchUpLeft(), held and GIVE_QUIET or 0)
            if wait > 0 and now - e.dueAt < RECHECK_SETTLE_MAX then
                later = min(later or wait, wait)
            else
                e.due, e.rechecks = false, e.rechecks + 1
                if IsInGuild() and e:Send({ t = e.T.R, h = e.module:GetDigestHash(), d = e.module:GetDigest() },
                    "GUILD", nil, "data") then
                    e.check = { sentAt = now }
                    JudgeLater(e, gen, now)
                end
            end
        end
    end
    if later then ScheduleRecheck(RECHECK_POSTPONE[1] + later, RECHECK_POSTPONE[2] + later) end
end

-- My HELLO goes out (its digest fields are being read): it starts the rechecks over. Whether anybody answers it is
-- judged like a recheck.
local function ArmRecheck()
    local now = GetTime()
    if armedAt == now then return end   -- (one HELLO reads every engine's field)
    armedAt = now
    recheckGen = recheckGen + 1
    fireAt = nil
    local gen = recheckGen
    local due = false
    for _, e in ipairs(engines) do
        -- (round 4: a recheck that was due stays due: a HELLO sent again soon after login (the council list or my
        -- roles came in) drew no answer when the others had answered me a moment before (one answer per round), and
        -- the dataset then counted as done while it still lacked what the recheck would have found)
        -- (and one the previous HELLO drew counts for this one: that catch-up is checked again)
        e.rechecks, e.check = 0, { sentAt = now, answered = e.check and e.check.answered or nil }
        due = due or e.due
        JudgeLater(e, gen, now)
    end
    if due then ScheduleRecheck(RECHECK_FIRST[1], RECHECK_FIRST[2]) end
end

-- XXR { h, d }: a member's recheck. Answered like a HELLO when I hold items they lack (or hold otherwise), or a grave
-- of a record they still list.
function Engine:OnRecheck(sender, msg, dist)
    if dist ~= "GUILD" or type(msg.h) ~= "string" or #msg.h > HASH_MAX then return end
    if msg.h == self.module:GetDigestHash() then return end
    local theirs = self:CleanDigest(msg.d)
    if not theirs then return end
    self:NotePeerDigest(sender, theirs)
    local offer = 0
    for item, h in pairs(self.module:GetDigest()) do
        if theirs[item] ~= h then offer = offer + 1 end
    end
    if offer == 0 and self.cfg.tombKeep ~= nil then
        local root, now = self:Root(false), Now()
        for item in pairs(root and theirs or {}) do
            local _, grave = self:Hidden(root, item, now)
            if grave then offer = offer + 1 end
        end
    end
    if offer > 0 then self:OnHelloDigest(sender, msg.h, offer) end
end

-- Registers the digest's messages (XXD, XXK, XXW) and, when given, the module's own XXU / XXG handlers; with
-- cfg.large, XXU / XXG / XXD may be as large as a council member's message. Then the HELLO field and the recheck.
-- Called from the module's OnInit.
function Engine:Register(onUpdate, onGive)
    local T = self.T
    local Comm = ns.Comm
    if Comm and Comm.Register then
        if onUpdate then Comm:Register(T.U, onUpdate) end
        Comm:Register(T.D, function(sender, msg, dist) self:OnDigest(sender, msg, dist) end)
        Comm:Register(T.K, function(sender, msg, dist) self:OnClaim(sender, msg, dist) end)
        Comm:Register(T.W, function(sender, msg, dist) self:OnWant(sender, msg, dist) end)
        if onGive then
            -- (an item given to me: my catch-up is still running, CatchUpLeft)
            Comm:Register(T.G, function(sender, msg, dist)
                if dist == "WHISPER" then
                    self.givenAt = GetTime()
                    if self.wantLeft > 0 then self.wantLeft = self.wantLeft - 1 end
                end
                return onGive(sender, msg, dist)
            end)
        end
        Comm:Register(T.R, function(sender, msg, dist) self:OnRecheck(sender, msg, dist) end)
        if self.cfg.large and Comm.AllowLarge then
            for _, t in ipairs({ T.U, T.G, T.D, T.R }) do Comm:AllowLarge(t, "data") end
        end
    end
    local Sync = ns.Sync
    if self.helloField and Sync and Sync.RegisterHelloField then
        local M = self.module
        local known = false
        for _, e in ipairs(engines) do known = known or e == self end
        if not known then engines[#engines + 1] = self end
        Sync:RegisterHelloField(self.helloField, self.helloOrder,
            function()
                ArmRecheck()
                return M:GetDigestHash()
            end,
            function(sender, v) M:OnHelloDigest(sender, v) end)
    end
end

---------------------------------------------------------------------------
-- Lists kept whole by a few writers, with one rev (the raid blacklist, the guest book's notes)
---------------------------------------------------------------------------

-- The rev rides in the HELLO (o.field, at o.order): a writer who holds a newer list than a member's sends it to them
-- after a short random delay; a member who holds an older one than a writer's asks that writer for it (o.query, a
-- whisper), and a writer answers that question with the list. One answer per member and o.limit seconds each way.
-- o: field, order, query (message type), rev() (my list's rev), serve() (may I send the list), writer(key) (may that
-- member write it), sendList(target), send(msg, dist, target, class), replyKey, askKey, queryKey (rate-limit key
-- prefixes), limit (seconds). Returns { Seen(sender, rev), OnQuery(sender, msg, dist), Register() }.
function DigestSync.RevList(o)
    local rl = {}

    -- Sync calls this for every HELLO (rev = the sender's rev; nil from clients without the field).
    function rl.Seen(sender, rev)
        if type(rev) ~= "number" or type(sender) ~= "string" then return end
        local mine = o.rev()
        if rev < mine and o.serve() then
            if RateLimit(o.replyKey .. sender, o.limit) then
                Util.RandomDelay(0.5, 3, function() o.sendList(sender) end)
            end
        elseif rev > mine and o.writer(sender) then
            if RateLimit(o.askKey .. sender, o.limit) then
                o.send({ t = o.query }, "WHISPER", sender, "ctrl")
            end
        end
    end

    -- o.query { }: a member asks me for the list.
    function rl.OnQuery(sender, _, dist)
        if dist ~= "WHISPER" or not o.serve() then return end
        if not RateLimit(o.queryKey .. sender, o.limit) then return end
        o.sendList(sender)
    end

    -- The question's handler and the HELLO field (from the module's OnInit).
    function rl.Register()
        local Comm = ns.Comm
        if Comm and Comm.Register then Comm:Register(o.query, rl.OnQuery) end
        local Sync = ns.Sync
        if Sync and Sync.RegisterHelloField then Sync:RegisterHelloField(o.field, o.order, o.rev, rl.Seen) end
    end

    return rl
end

---------------------------------------------------------------------------
-- Bucket digests (the Ledger's days, the raid log's weeks)
---------------------------------------------------------------------------

-- { [bucket] = hash(list) } of { [bucket] = { item string, ... } } (each list sorted first, in place).
function DigestSync.BucketDigest(perBucket, hash)
    local out = {}
    for b, list in pairs(perBucket) do
        tsort(list)
        out[b] = hash(list)
    end
    return out
end

-- The buckets of a peer's digest whose hash differs from mine (in the order pairs gives them). Looks at o.maxSeen
-- entries at most (an untrusted table); a bucket counts when it is a whole number from o.lo to o.hi and its hash
-- passes o.hashOk(h); o.accept(bucket), when given, may still leave it out; stops after o.maxPick buckets.
function DigestSync.DiffBuckets(theirs, mine, o)
    local out, seen = {}, 0
    for b, h in pairs(theirs) do
        seen = seen + 1
        if seen > o.maxSeen then break end
        if type(b) == "number" and b == floor(b) and b >= o.lo and b <= o.hi and o.hashOk(h) and mine[b] ~= h
            and (not o.accept or o.accept(b)) then
            out[#out + 1] = b
            if o.maxPick and #out >= o.maxPick then break end
        end
    end
    return out
end

---------------------------------------------------------------------------
-- Set-up
---------------------------------------------------------------------------

-- A sync engine for one module (the fields at the top of this file). Installs GetDigest, GetDigestHash and
-- OnHelloDigest on the module unless it has its own.
function DigestSync.New(cfg)
    local p = cfg.prefix
    local self = setmetatable({
        cfg = cfg,
        module = cfg.module,
        bucket = cfg.bucket,
        kinds = cfg.kinds,
        kindSet = {},
        T = { U = p .. "U", D = p .. "D", K = p .. "K", W = p .. "W", G = p .. "G", R = p .. "R" },
        maxItems = cfg.maxItems,
        maxItemLen = cfg.maxItemLen,
        itemPattern = cfg.itemPattern,
        keepHash = cfg.keepHash and true or false,
        helloField = cfg.helloField,
        helloOrder = cfg.helloOrder,
        roundSeen = {},          -- [key] = { at = GetTime() (, h) }: a digest to that client was seen / claimed
        answeredAt = -1000,      -- GetTime() I answered the first digest of my own round
        givenAt = -1000,         -- GetTime() an item was last given to me (XXG)
        wantLeft = 0,            -- items I asked for in my last round, not given yet (as counted by XXG)
        check = nil,             -- my HELLO or recheck waits for an answer: { sentAt, answered }
        due = false,             -- a recheck is due (dueAt: since when)
        rechecks = 0,            -- rechecks sent since my HELLO
        done = false,            -- my last HELLO or recheck drew no answer (nobody online held anything I lacked)
        wantedFrom = {},         -- [item] = { m, at }: asked from that relayer (SendWant), for AskHeld
        roundWanted = {},        -- [item] = true: asked for in my current round (OnDigest)
        peerDigest = {},         -- [member] = { d, at }: their last digest heard on GUILD (KnownHolders)
        gaveTo = {}, gaveN = 0,  -- [member .. "|" .. item .. "|" .. hash] = { at, mark }: given (SendItem)
        idCounter = 0,
    }, Engine)
    for _, k in ipairs(cfg.kinds) do self.kindSet[k] = true end
    local M = cfg.module
    if M then
        local eng = self
        if not M.GetDigest then M.GetDigest = function() return eng:GetDigest() end end
        if not M.GetDigestHash then M.GetDigestHash = function() return eng:GetDigestHash() end end
        if not M.OnHelloDigest then
            M.OnHelloDigest = function(_, sender, hash) return eng:OnHelloDigest(sender, hash) end
        end
    end
    return self
end

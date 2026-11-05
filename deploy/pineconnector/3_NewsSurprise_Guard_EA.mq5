//+------------------------------------------------------------------+
//|  NewsSurprise_Guard_EA.mq5                                       |
//|  1) US/CA economic-news surprise strategy (ETF-bot round 10b/11) |
//|  2) Account-wide FTMO safety guard for ALL strategies            |
//|     (incl. the PineConnector Nasdaq + gold trades)               |
//+------------------------------------------------------------------+
//  STRATEGY (frozen research rules)
//   • High-importance US and Canadian releases with actual + forecast.
//   • Surprise z = (actual - forecast) / std of that event's past surprises (>= 10 past releases);
//     sign flipped for "Unemployment Rate" and "Jobless Claims" (lower = good for the currency).
//     Energy inventory releases are ignored.
//   • |z| > 0.5: 5 minutes after the release, trade in the surprise direction:
//       USD good  -> sell EURUSD, GBPUSD, AUDUSD, XAUUSD; buy USDJPY, USDCAD
//       CAD good  -> sell USDCAD
//     Releases at the same minute are netted (e.g. two USD-good + one USD-bad = one unit USD-good).
//   • Size: a 1-day-volatility move = InpRiskPerUnit % of equity per unit.
//   • Stop = 0.4 x daily volatility; moved to break-even at +1R; position closed after 60 minutes.
//  GUARD
//   • Day loss >= InpDayStopPct % of start-of-day equity -> close every position on the account
//     and keep closing new ones until the next server day.
//   • Equity below the start balance by InpHalfBelowPct % -> news trades at half size.
//  DATA SOURCE
//   • Live / demo: MT5's built-in economic calendar.
//   • Strategy Tester (calendar not available there): news_events.csv (copy into MQL5\Files).
//+------------------------------------------------------------------+
#property copyright "ETF-bot research"
#property version   "1.00"
#property tester_file "news_events.csv"
#include <Trade\Trade.mqh>

input group "Symbols (FTMO names)"
input string InpEURUSD = "EURUSD";
input string InpGBPUSD = "GBPUSD";
input string InpAUDUSD = "AUDUSD";
input string InpUSDJPY = "USDJPY";
input string InpUSDCAD = "USDCAD";
input string InpXAUUSD = "XAUUSD";

input group "News strategy"
input bool   InpTradeNews     = true;     // trade the news strategy
input double InpRiskPerUnit   = 0.15;     // % of equity lost on a 1-daily-vol move, per unit
input double InpZThreshold    = 0.5;      // |z| needed
input int    InpDelayMinutes  = 5;        // enter this many minutes after the release
input int    InpHoldMinutes   = 60;       // close after this many minutes
input double InpStopDvol      = 0.4;      // stop distance in daily-vol units (break-even at +1R)
input int    InpMinHistory    = 10;       // past releases needed to measure surprise size
input bool   InpUseCsv        = false;    // force CSV events (always on in the Strategy Tester)
input string InpCsvFile       = "news_events.csv";

input group "FTMO safety guard (whole account)"
input bool   InpGuardOn       = true;
input double InpDayStopPct    = 2.0;      // close everything after this daily loss %
input double InpHalfBelowPct  = 5.0;      // half size when equity is this % below start balance
input double InpStartBalance  = 100000;   // challenge / account start balance
input bool   InpGuardAll      = true;     // guard closes ALL positions (incl. PineConnector trades)

input group "Time"
input int    InpServerGMT     = -100;     // server GMT offset; -100 = auto (GMT+2, +3 in US summer time, FTMO style)
input long   InpMagic         = 26110510; // unique ID for news trades (PineConnector uses its own)
input bool   InpSkipGoldIfNetting = true; // on a NETTING account, don't trade gold (it would merge with the gold strategy)

CTrade trade;
string g_syms[6];
int    g_orient[6];          // +1 if USD is the base currency (USD good -> buy), -1 otherwise
datetime g_dayStart = 0;
double g_dayStartEq = 0;
bool   g_locked = false;
bool   g_skip[6];

struct NewsPos { ulong ticket; string sym; datetime opened; double entry; double risk; int dir; bool be; };
NewsPos g_pos[];

// CSV events (tester)
datetime g_evTime[]; string g_evCur[]; double g_evZ[]; int g_evNext = 0;
// processed release times (live)
datetime g_done[];

//+------------------------------------------------------------------+
datetime NthSunday(int y, int m, int n)
  {
   datetime first = StringToTime(StringFormat("%04d.%02d.01 00:00", y, m));
   MqlDateTime d; TimeToStruct(first, d);
   int day = 1 + (7 - d.day_of_week) % 7 + 7 * (n - 1);
   return StringToTime(StringFormat("%04d.%02d.%02d 00:00", y, m, day));
  }
bool IsUSDST(datetime utc)
  {
   MqlDateTime d; TimeToStruct(utc, d);
   datetime s = NthSunday(d.year, 3, 2) + 7 * 3600;    // 2:00 EST
   datetime e = NthSunday(d.year, 11, 1) + 6 * 3600;   // 2:00 EDT
   return (utc >= s && utc < e);
  }
int ServerOffsetHours(datetime utc)
  {
   if(InpServerGMT != -100) return InpServerGMT;
   return 2 + (IsUSDST(utc) ? 1 : 0);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_syms[0] = InpEURUSD; g_orient[0] = -1;
   g_syms[1] = InpGBPUSD; g_orient[1] = -1;
   g_syms[2] = InpAUDUSD; g_orient[2] = -1;
   g_syms[3] = InpUSDJPY; g_orient[3] = +1;
   g_syms[4] = InpUSDCAD; g_orient[4] = +1;
   g_syms[5] = InpXAUUSD; g_orient[5] = -1;
   bool netting = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
   for(int i = 0; i < 6; i++)
     {
      g_skip[i] = (g_syms[i] == "");
      if(!g_skip[i] && !SymbolSelect(g_syms[i], true))
        { PrintFormat("WARNING: symbol %s not found - skipped", g_syms[i]); g_skip[i] = true; }
     }
   if(netting)
     {
      Print("WARNING: this is a NETTING account - positions on the same symbol merge. Use a HEDGING account for this plan.");
      if(InpSkipGoldIfNetting) { g_skip[5] = true; Print("Gold news trades disabled so they can't merge with the gold strategy."); }
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   if(UseCsv() && !LoadCsv())
     {
      Print("ERROR: could not read ", InpCsvFile, " (put it in MQL5\\Files)");
      return INIT_FAILED;
     }
   EventSetTimer(5);
   ResetDay();
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int reason) { EventKillTimer(); }
bool UseCsv() { return (InpUseCsv || (bool)MQLInfoInteger(MQL_TESTER)); }

//+------------------------------------------------------------------+
bool LoadCsv()
  {
   int h = FileOpen(InpCsvFile, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return false;
   int n = 0;
   // header
   for(int k = 0; k < 4 && !FileIsEnding(h); k++) FileReadString(h);
   while(!FileIsEnding(h))
     {
      string ts = FileReadString(h);
      if(ts == "") break;
      string cur = FileReadString(h);
      double z = StringToDouble(FileReadString(h));
      FileReadString(h);                          // title (unused)
      datetime utc = StringToTime(ts);
      ArrayResize(g_evTime, n + 1); ArrayResize(g_evCur, n + 1); ArrayResize(g_evZ, n + 1);
      g_evTime[n] = utc + ServerOffsetHours(utc) * 3600;   // -> server time
      g_evCur[n] = cur; g_evZ[n] = z; n++;
     }
   FileClose(h);
   PrintFormat("Loaded %d news events from %s", n, InpCsvFile);
   return (n > 0);
  }

//+------------------------------------------------------------------+
void OnTick()  { Step(); }
void OnTimer() { Step(); }

void Step()
  {
   Guard();
   ManagePositions();
   if(InpTradeNews && !g_locked)
     {
      if(UseCsv()) ProcessCsv();
      else ProcessCalendar();
     }
  }

//+------------------------------------------------------------------+
void ResetDay()
  {
   MqlDateTime d; TimeToStruct(TimeCurrent(), d);
   d.hour = 0; d.min = 0; d.sec = 0;
   g_dayStart = StructToTime(d);
   g_dayStartEq = AccountInfoDouble(ACCOUNT_EQUITY);
   g_locked = false;
  }

void Guard()
  {
   if(!InpGuardOn) return;
   if(TimeCurrent() >= g_dayStart + 86400) ResetDay();
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!g_locked && eq <= g_dayStartEq * (1.0 - InpDayStopPct / 100.0))
     {
      g_locked = true;
      PrintFormat("GUARD: daily loss %.2f%% reached - closing all positions until tomorrow",
                  (eq / g_dayStartEq - 1) * 100);
     }
   if(g_locked) CloseAll();
  }

void CloseAll()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(!InpGuardAll && PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      trade.PositionClose(t);
     }
   ArrayResize(g_pos, 0);
  }

//+------------------------------------------------------------------+
double DailyVol(string sym)
  {
   double c[];
   if(CopyClose(sym, PERIOD_D1, 1, 21, c) < 21) return 0.0;
   double r[20], m = 0;
   for(int i = 1; i < 21; i++) { r[i - 1] = c[i] / c[i - 1] - 1.0; m += r[i - 1]; }
   m /= 20.0;
   double v = 0;
   for(int i = 0; i < 20; i++) v += (r[i] - m) * (r[i] - m);
   return MathSqrt(v / 19.0);
  }

double LotsFor(string sym, double dvol, double units)
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double mult = (eq < InpStartBalance * (1.0 - InpHalfBelowPct / 100.0)) ? 0.5 : 1.0;
   double price = SymbolInfoDouble(sym, SYMBOL_ASK);
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(price <= 0 || tv <= 0 || ts <= 0 || dvol <= 0) return 0.0;
   double lossPerLot = (dvol * price / ts) * tv;              // loss of 1 lot on a 1-daily-vol move
   double lots = eq * InpRiskPerUnit / 100.0 * units * mult / lossPerLot;
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   lots = MathFloor(lots / step) * step;
   if(lots < vmin) return 0.0;
   return MathMin(lots, vmax);
  }

void OpenNews(int symIdx, int dir, double units, string tag)
  {
   string sym = g_syms[symIdx];
   double dvol = DailyVol(sym);
   double lots = LotsFor(sym, dvol, units);
   if(lots <= 0) { PrintFormat("skip %s: size too small or no data", sym); return; }
   double price = (dir > 0) ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   double risk = InpStopDvol * dvol * price;
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double sl = NormalizeDouble(price - dir * risk, digits);
   bool ok = (dir > 0) ? trade.Buy(lots, sym, 0, sl, 0, "NEWS") : trade.Sell(lots, sym, 0, sl, 0, "NEWS");
   if(!ok) { PrintFormat("order failed %s: %d", sym, trade.ResultRetcode()); return; }
   ulong t = trade.ResultOrder();
   if(PositionSelectByTicket(t) == false)
     {
      // on netting/hedging accounts the position ticket can differ from the order ticket
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong pt = PositionGetTicket(i);
         if(PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == InpMagic) { t = pt; break; }
        }
     }
   int n = ArraySize(g_pos); ArrayResize(g_pos, n + 1);
   g_pos[n].ticket = t; g_pos[n].sym = sym; g_pos[n].opened = TimeCurrent();
   g_pos[n].entry = trade.ResultPrice() > 0 ? trade.ResultPrice() : price;
   g_pos[n].risk = risk; g_pos[n].dir = dir; g_pos[n].be = false;
   PrintFormat("NEWS %s %s %.2f lots (units %.0f, dvol %.4f) %s", dir > 0 ? "BUY" : "SELL", sym, lots, units, dvol, tag);
  }

void ManagePositions()
  {
   for(int i = ArraySize(g_pos) - 1; i >= 0; i--)
     {
      if(!PositionSelectByTicket(g_pos[i].ticket) || PositionGetInteger(POSITION_MAGIC) != InpMagic)
        { ArrayRemove(g_pos, i, 1); continue; }
      if(TimeCurrent() >= g_pos[i].opened + InpHoldMinutes * 60)
        { trade.PositionClose(g_pos[i].ticket); ArrayRemove(g_pos, i, 1); continue; }
      if(!g_pos[i].be)
        {
         double px = (g_pos[i].dir > 0) ? SymbolInfoDouble(g_pos[i].sym, SYMBOL_BID) : SymbolInfoDouble(g_pos[i].sym, SYMBOL_ASK);
         if(g_pos[i].dir * (px - g_pos[i].entry) >= g_pos[i].risk)
           {
            int digits = (int)SymbolInfoInteger(g_pos[i].sym, SYMBOL_DIGITS);
            if(trade.PositionModify(g_pos[i].ticket, NormalizeDouble(g_pos[i].entry, digits), 0))
               g_pos[i].be = true;
           }
        }
     }
  }

//+------------------------------------------------------------------+
//  Netting a release minute into trades
void Execute(int kUsd, int kCad, string tag)
  {
   for(int i = 0; i < 6; i++)
     {
      int k = g_orient[i] * kUsd;
      if(i == 4) k = kUsd - kCad;                 // USDCAD: USD good -> up, CAD good -> down
      if(k == 0 || g_skip[i]) continue;
      OpenNews(i, k > 0 ? 1 : -1, MathAbs(k), tag);
     }
  }

void ProcessCsv()
  {
   datetime now = TimeCurrent();
   while(g_evNext < ArraySize(g_evTime) && g_evTime[g_evNext] + InpDelayMinutes * 60 + 120 < now) g_evNext++;   // missed (too late)
   if(g_evNext >= ArraySize(g_evTime)) return;
   datetime t = g_evTime[g_evNext];
   if(now < t + InpDelayMinutes * 60) return;
   int kUsd = 0, kCad = 0;
   while(g_evNext < ArraySize(g_evTime) && g_evTime[g_evNext] == t)
     {
      if(MathAbs(g_evZ[g_evNext]) > InpZThreshold)
        {
         int s = (g_evZ[g_evNext] > 0) ? 1 : -1;
         if(g_evCur[g_evNext] == "USD") kUsd += s; else if(g_evCur[g_evNext] == "CAD") kCad += s;
        }
      g_evNext++;
     }
   if(kUsd != 0 || kCad != 0) Execute(kUsd, kCad, TimeToString(t, TIME_DATE | TIME_MINUTES));
  }

bool IsDone(datetime t)
  {
   for(int i = 0; i < ArraySize(g_done); i++) if(g_done[i] == t) return true;
   return false;
  }

bool Inverse(string name)
  {
   return (StringFind(name, "Unemployment Rate") >= 0 || StringFind(name, "Jobless Claims") >= 0);
  }
bool Excluded(string name)
  {
   return (StringFind(name, "Crude") >= 0 || StringFind(name, "Gasoline") >= 0 ||
           StringFind(name, "Natural Gas") >= 0 || StringFind(name, "EIA") >= 0);
  }

double SurpriseZ(MqlCalendarValue &v, MqlCalendarEvent &ev)
  {
   MqlCalendarValue h[];
   if(!CalendarValueHistoryByEvent(v.event_id, h, v.time - 12 * 365 * 86400, v.time - 60)) return 0.0;
   double s[]; int n = 0;
   for(int i = 0; i < ArraySize(h); i++)
      if(h[i].HasActualValue() && h[i].HasForecastValue())
        { ArrayResize(s, n + 1); s[n++] = h[i].GetActualValue() - h[i].GetForecastValue(); }
   if(n < InpMinHistory) return 0.0;
   double m = 0; for(int i = 0; i < n; i++) m += s[i]; m /= n;
   double var = 0; for(int i = 0; i < n; i++) var += (s[i] - m) * (s[i] - m);
   double sd = MathSqrt(var / (n - 1));
   if(sd <= 0) return 0.0;
   double z = (v.GetActualValue() - v.GetForecastValue()) / sd;
   return Inverse(ev.name) ? -z : z;
  }

void ProcessCalendar()
  {
   datetime now = TimeTradeServer();
   string curs[2] = {"USD", "CAD"};
   // collect release minutes in the entry window
   datetime times[]; int kU[], kC[]; int nt = 0;
   for(int c = 0; c < 2; c++)
     {
      MqlCalendarValue vals[];
      int n = CalendarValueHistory(vals, now - 3 * 3600, now, NULL, curs[c]);
      for(int i = 0; i < n; i++)
        {
         datetime t = vals[i].time;
         if(now < t + InpDelayMinutes * 60 || now > t + InpDelayMinutes * 60 + 120 || IsDone(t)) continue;
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev)) continue;
         if(ev.importance != CALENDAR_IMPORTANCE_HIGH || Excluded(ev.name)) continue;
         if(!vals[i].HasActualValue() || !vals[i].HasForecastValue()) continue;
         double z = SurpriseZ(vals[i], ev);
         int j = -1;
         for(int q = 0; q < nt; q++) if(times[q] == t) j = q;
         if(j < 0) { ArrayResize(times, nt + 1); ArrayResize(kU, nt + 1); ArrayResize(kC, nt + 1); times[nt] = t; kU[nt] = 0; kC[nt] = 0; j = nt++; }
         PrintFormat("release %s %s z=%.2f", curs[c], ev.name, z);
         if(MathAbs(z) > InpZThreshold)
           {
            if(c == 0) kU[j] += (z > 0 ? 1 : -1); else kC[j] += (z > 0 ? 1 : -1);
           }
        }
     }
   for(int q = 0; q < nt; q++)
     {
      int d = ArraySize(g_done); ArrayResize(g_done, d + 1); g_done[d] = times[q];
      if(kU[q] != 0 || kC[q] != 0) Execute(kU[q], kC[q], TimeToString(times[q], TIME_DATE | TIME_MINUTES));
     }
  }
//+------------------------------------------------------------------+

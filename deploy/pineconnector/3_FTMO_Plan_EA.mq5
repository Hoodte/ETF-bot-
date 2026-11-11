//+------------------------------------------------------------------+
//|  FTMO_Plan_EA.mq5  v1.11                                         |
//|  Runs inside MT5 (same account as PineConnector):                |
//|   A) US/CA economic-news surprise strategy (6 instruments)       |
//|   B) Nasdaq lunch-RSI 1:3 strategy (replaces the Pine version)   |
//|   C) Account-wide FTMO safety: -2% daily stop, -8% overall brake,|
//|      half size below -5%                                         |
//|   + spread filter on news entries, trade log file, phone alerts  |
//|  The GOLD strategy stays on TradingView/PineConnector (it needs  |
//|  dollar-index, TIP and COT data that MT5 does not provide).      |
//+------------------------------------------------------------------+
//  NEWS RULES (frozen research, ETF-bot rounds 10b/11)
//   High-importance US/CA releases with actual + forecast. z = (actual - forecast) / std of that
//   event's past surprises (>= 10); sign flipped for "Unemployment Rate"/"Jobless Claims";
//   energy inventories ignored. |z| > 0.5 -> 5 min after release trade the surprise:
//   USD good: sell EURUSD, GBPUSD, AUDUSD, XAUUSD; buy USDJPY, USDCAD.  CAD good: sell USDCAD.
//   Same-minute releases are netted. Size: 1 daily-vol move = InpRiskPerUnit % equity per unit.
//   Stop 0.4 daily-vol, break-even at +1R, close after 60 min.
//  NASDAQ RULES (backtest-bot nas100_m15 pattern + round-11 exit)
//   M15 bar that STARTS 11:30-13:29 New York closes with RSI(14) > 70 -> buy at market.
//   Stop 1 x ATR(14), target 3 x ATR(14) of the signal bar. One trade per NY day. Flat at 15:55 NY.
//   Risk InpNasRiskPct % of equity per trade.
//  DATA: live/demo = MT5 economic calendar; Strategy Tester = news_events.csv (MQL5\Files).
//+------------------------------------------------------------------+
#property copyright "ETF-bot research"
#property version   "1.11"
#property tester_file "news_events.csv"
#include <Trade\Trade.mqh>

input group "Symbols (FTMO names)"
input string InpEURUSD = "EURUSD";
input string InpGBPUSD = "GBPUSD";
input string InpAUDUSD = "AUDUSD";
input string InpUSDJPY = "USDJPY";
input string InpUSDCAD = "USDCAD";
input string InpXAUUSD = "XAUUSD";        // leave blank to stop news trades on gold
input string InpUS100  = "US100.cash";

input group "A) News strategy"
input bool   InpTradeNews     = true;
input double InpRiskPerUnit   = 0.15;     // % of equity lost on a 1-daily-vol move, per unit
input double InpZThreshold    = 0.5;
input int    InpDelayMinutes  = 5;
input int    InpHoldMinutes   = 60;
input double InpStopDvol      = 0.4;      // stop distance in daily-vol units (break-even at +1R)
input int    InpMinHistory    = 10;
input double InpMaxSpreadMult = 2.5;      // skip a news trade if spread > this x normal spread
input bool   InpUseCsv        = false;    // force CSV events (always used in the Strategy Tester)
input string InpCsvFile       = "news_events.csv";
input int    InpCalCheckDays  = 14;       // at start-up, list the last N days of releases the EA can see (0 = off)
input bool   InpPushReleases  = true;     // phone notification for every release the EA reads (traded or not)
input long   InpMagicNews     = 26110510;

input group "B) Nasdaq lunch-RSI (do NOT also run the Pine Nasdaq script)"
input bool   InpTradeNasdaq   = true;
input double InpNasRiskPct    = 1.1;      // % of equity risked per trade (stop hit)
input double InpNasStopAtr    = 1.0;
input double InpNasTgtAtr     = 3.0;
input double InpNasRsiLevel   = 70.0;
input long   InpMagicNas      = 26110511;

input group "C) FTMO safety (whole account)"
input bool   InpGuardOn       = true;
input double InpDayStopPct    = 2.0;      // close everything after this daily loss %
input double InpBrakePct      = 8.0;      // stop ALL trading if equity falls this % below start balance
input double InpHalfBelowPct  = 5.0;      // half size when equity is this % below start balance
input double InpStartBalance  = 100000;
input bool   InpGuardAll      = true;     // guard closes ALL positions (incl. PineConnector gold)
input bool   InpResetBrake    = false;    // set true once to clear a triggered brake
input bool   InpSkipGoldIfNetting = true;

input group "Alerts & log"
input bool   InpPush          = true;     // MT5 push notifications (set your MetaQuotes ID in MT5 options)
input string InpLogFile       = "ftmo_plan_log.csv";

input group "Time"
input int    InpServerGMT     = -100;     // -100 = auto (GMT+2, +3 in US summer time, FTMO style)

CTrade trade;
string g_syms[6];
int    g_orient[6];
bool   g_skip[6];
double g_spreadEma[6];
datetime g_dayStart = 0;
double g_dayStartEq = 0;
bool   g_locked = false;
bool   g_brake = false;
string BRAKE_GV = "FTMOPLAN_BRAKE";

struct NewsPos { ulong ticket; string sym; datetime opened; double entry; double risk; int dir; bool be; };
NewsPos g_pos[];
datetime g_evTime[]; string g_evCur[]; double g_evZ[]; int g_evNext = 0;
datetime g_done[];

int g_hRsi = INVALID_HANDLE, g_hAtr = INVALID_HANDLE;
datetime g_lastNasBar = 0;
int g_nasTradedDay = -1;

//+------------------------------------------------------------------+
//  time helpers
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
   datetime s = NthSunday(d.year, 3, 2) + 7 * 3600;
   datetime e = NthSunday(d.year, 11, 1) + 6 * 3600;
   return (utc >= s && utc < e);
  }
int ServerOffsetHours(datetime utc)
  {
   if(InpServerGMT != -100) return InpServerGMT;
   return 2 + (IsUSDST(utc) ? 1 : 0);
  }
datetime ServerToUTC(datetime srv) { return srv - ServerOffsetHours(srv - 2 * 3600) * 3600; }
datetime UTCToNY(datetime utc)     { return utc - (IsUSDST(utc) ? 4 : 5) * 3600; }
int NYMinutes(datetime srv)  { MqlDateTime d; TimeToStruct(UTCToNY(ServerToUTC(srv)), d); return d.hour * 60 + d.min; }
int NYDayKey(datetime srv)   { MqlDateTime d; TimeToStruct(UTCToNY(ServerToUTC(srv)), d); return d.year * 10000 + d.mon * 100 + d.day; }

//+------------------------------------------------------------------+
//  log + alerts
void LogLine(string line)
  {
   int h = FileOpen(InpLogFile, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE) return;
   if(FileSize(h) == 0) FileWriteString(h, "server_time,event,strategy,symbol,dir,lots,intended_price,fill_price,spread_points,detail\r\n");
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + "," + line + "\r\n");
   FileClose(h);
  }
void Notify(string msg)
  {
   Print(msg);
   if(InpPush && !(bool)MQLInfoInteger(MQL_TESTER)) SendNotification("FTMO plan: " + msg);
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
      g_spreadEma[i] = g_skip[i] ? 0 : (double)SymbolInfoInteger(g_syms[i], SYMBOL_SPREAD);
     }
   if(netting)
     {
      Print("WARNING: NETTING account - positions on the same symbol merge. Use a HEDGING account for this plan.");
      if(InpSkipGoldIfNetting) { g_skip[5] = true; Print("Gold news trades disabled so they can't merge with the gold strategy."); }
     }
   if(InpTradeNasdaq)
     {
      if(!SymbolSelect(InpUS100, true)) { PrintFormat("ERROR: %s not found", InpUS100); return INIT_FAILED; }
      g_hRsi = iRSI(InpUS100, PERIOD_M15, 14, PRICE_CLOSE);
      g_hAtr = iATR(InpUS100, PERIOD_M15, 14);
      if(g_hRsi == INVALID_HANDLE || g_hAtr == INVALID_HANDLE) { Print("ERROR: indicator handles"); return INIT_FAILED; }
     }
   if(InpResetBrake) GlobalVariableDel(BRAKE_GV);
   g_brake = GlobalVariableCheck(BRAKE_GV) && !(bool)MQLInfoInteger(MQL_TESTER);
   if(g_brake) Notify("overall loss brake is ACTIVE - no trading (set InpResetBrake=true to clear)");
   if(InpTradeNews && UseCsv() && !LoadCsv())
     {
      Print("ERROR: could not read ", InpCsvFile, " (put it in MQL5\\Files)");
      return INIT_FAILED;
     }
   EventSetTimer(5);
   ResetDay();
   Notify(StringFormat("EA started. news=%s nasdaq=%s guard=%s account=%s", InpTradeNews ? "on" : "off",
                       InpTradeNasdaq ? "on" : "off", InpGuardOn ? "on" : "off", netting ? "NETTING" : "hedging"));
   if(InpTradeNews && !UseCsv() && InpCalCheckDays > 0) CalendarReport(InpCalCheckDays);
   return INIT_SUCCEEDED;
  }
// v1.11 diagnostic: list recent high-impact USD/CAD releases with MT5's actual, forecast and our z-score
void CalendarReport(int days)
  {
   datetime now = TimeTradeServer(); string curs[2] = {"USD", "CAD"};
   int seen = 0, big = 0; string summary = "";
   for(int c = 0; c < 2; c++)
     {
      MqlCalendarValue vals[];
      int n = CalendarValueHistory(vals, now - days * 86400, now, NULL, curs[c]);
      if(n < 0) { PrintFormat("CALCHECK: CalendarValueHistory failed for %s, error %d", curs[c], GetLastError()); continue; }
      for(int i = 0; i < n; i++)
        {
         MqlCalendarEvent ev;
         if(!CalendarEventById(vals[i].event_id, ev)) continue;
         if(ev.importance != CALENDAR_IMPORTANCE_HIGH || Excluded(ev.name)) continue;
         bool ha = vals[i].HasActualValue(), hf = vals[i].HasForecastValue();
         double z = (ha && hf) ? SurpriseZ(vals[i], ev) : 0.0;
         seen++; if(MathAbs(z) > InpZThreshold) big++;
         PrintFormat("CALCHECK %s %s | %s | actual=%s forecast=%s z=%.2f%s", curs[c], TimeToString(vals[i].time), ev.name,
                     ha ? DoubleToString(vals[i].GetActualValue(), 3) : "none", hf ? DoubleToString(vals[i].GetForecastValue(), 3) : "none",
                     z, MathAbs(z) > InpZThreshold ? "  <-- would trade" : "");
         if(StringFind(ev.name, "CPI") >= 0 && StringLen(summary) < 150)
            summary += StringFormat(" %s a%s f%s z%.1f;", ev.name, ha ? DoubleToString(vals[i].GetActualValue(), 1) : "-",
                                    hf ? DoubleToString(vals[i].GetForecastValue(), 1) : "-", z);
        }
     }
   Notify(StringFormat("Calendar check %dd: %d high-impact releases seen, %d above z %.1f.%s", days, seen, big, InpZThreshold, summary));
  }
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(g_hRsi != INVALID_HANDLE) IndicatorRelease(g_hRsi);
   if(g_hAtr != INVALID_HANDLE) IndicatorRelease(g_hAtr);
  }
bool UseCsv() { return (InpUseCsv || (bool)MQLInfoInteger(MQL_TESTER)); }

bool LoadCsv()
  {
   int h = FileOpen(InpCsvFile, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return false;
   int n = 0;
   for(int k = 0; k < 4 && !FileIsEnding(h); k++) FileReadString(h);
   while(!FileIsEnding(h))
     {
      string ts = FileReadString(h);
      if(ts == "") break;
      string cur = FileReadString(h);
      double z = StringToDouble(FileReadString(h));
      FileReadString(h);
      datetime utc = StringToTime(ts);
      ArrayResize(g_evTime, n + 1); ArrayResize(g_evCur, n + 1); ArrayResize(g_evZ, n + 1);
      g_evTime[n] = utc + ServerOffsetHours(utc) * 3600;
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
   UpdateSpreads();
   ManagePositions();
   if(g_locked || g_brake) return;
   if(InpTradeNews) { if(UseCsv()) ProcessCsv(); else ProcessCalendar(); }
   if(InpTradeNasdaq) NasdaqStep();
  }

//+------------------------------------------------------------------+
//  C) safety
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
   if(!g_brake && eq <= InpStartBalance * (1.0 - InpBrakePct / 100.0))
     {
      g_brake = true;
      if(!(bool)MQLInfoInteger(MQL_TESTER)) GlobalVariableSet(BRAKE_GV, 1);
      Notify(StringFormat("OVERALL BRAKE: equity %.0f is %.1f%% below start - all trading stopped", eq, InpBrakePct));
      LogLine("brake,ALL,,,,,,," + DoubleToString(eq, 2));
     }
   if(!g_locked && eq <= g_dayStartEq * (1.0 - InpDayStopPct / 100.0))
     {
      g_locked = true;
      Notify(StringFormat("DAILY STOP: day loss %.2f%% - closing all positions until tomorrow", (eq / g_dayStartEq - 1) * 100));
      LogLine("daily_stop,ALL,,,,,,," + DoubleToString(eq, 2));
     }
   if(g_locked || g_brake) CloseAll();
  }
void CloseAll()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(!InpGuardAll && mg != InpMagicNews && mg != InpMagicNas) continue;
      trade.PositionClose(t);
     }
   ArrayResize(g_pos, 0);
  }
double SizeMult()
  {
   return (AccountInfoDouble(ACCOUNT_EQUITY) < InpStartBalance * (1.0 - InpHalfBelowPct / 100.0)) ? 0.5 : 1.0;
  }

//+------------------------------------------------------------------+
//  spread tracking (normal spread = slow average, ignoring spikes)
void UpdateSpreads()
  {
   for(int i = 0; i < 6; i++)
     {
      if(g_skip[i]) continue;
      double s = (double)SymbolInfoInteger(g_syms[i], SYMBOL_SPREAD);
      if(s <= 0) continue;
      if(g_spreadEma[i] <= 0) { g_spreadEma[i] = s; continue; }
      if(s < 3.0 * g_spreadEma[i]) g_spreadEma[i] += (s - g_spreadEma[i]) / 2000.0;
     }
  }

//+------------------------------------------------------------------+
//  A) news
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
double NormLots(string sym, double lots)
  {
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   if(step <= 0) return 0.0;
   lots = MathFloor(lots / step) * step;
   if(lots < vmin) return 0.0;
   return MathMin(lots, vmax);
  }
double NewsLots(string sym, double dvol, double units)
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double price = SymbolInfoDouble(sym, SYMBOL_ASK);
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(price <= 0 || tv <= 0 || ts <= 0 || dvol <= 0) return 0.0;
   double lossPerLot = (dvol * price / ts) * tv;
   return NormLots(sym, eq * InpRiskPerUnit / 100.0 * units * SizeMult() / lossPerLot);
  }
void OpenNews(int idx, int dir, double units, string tag)
  {
   string sym = g_syms[idx];
   double spread = (double)SymbolInfoInteger(sym, SYMBOL_SPREAD);
   if(g_spreadEma[idx] > 0 && spread > InpMaxSpreadMult * g_spreadEma[idx])
     {
      PrintFormat("skip %s: spread %.0f > %.1f x normal %.1f", sym, spread, InpMaxSpreadMult, g_spreadEma[idx]);
      LogLine(StringFormat("skip_spread,NEWS,%s,%d,,,,%.0f,normal %.1f", sym, dir, spread, g_spreadEma[idx]));
      return;
     }
   double dvol = DailyVol(sym);
   double lots = NewsLots(sym, dvol, units);
   if(lots <= 0) { PrintFormat("skip %s: size too small or no data", sym); return; }
   double price = (dir > 0) ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   double risk = InpStopDvol * dvol * price;
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double sl = NormalizeDouble(price - dir * risk, digits);
   trade.SetExpertMagicNumber(InpMagicNews);
   bool ok = (dir > 0) ? trade.Buy(lots, sym, 0, sl, 0, "NEWS") : trade.Sell(lots, sym, 0, sl, 0, "NEWS");
   if(!ok) { PrintFormat("order failed %s: %d", sym, trade.ResultRetcode()); return; }
   ulong t = trade.ResultOrder();
   if(!PositionSelectByTicket(t))
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong pt = PositionGetTicket(i);
         if(PositionGetString(POSITION_SYMBOL) == sym && PositionGetInteger(POSITION_MAGIC) == InpMagicNews) { t = pt; break; }
        }
   double fill = trade.ResultPrice() > 0 ? trade.ResultPrice() : price;
   int n = ArraySize(g_pos); ArrayResize(g_pos, n + 1);
   g_pos[n].ticket = t; g_pos[n].sym = sym; g_pos[n].opened = TimeCurrent();
   g_pos[n].entry = fill; g_pos[n].risk = risk; g_pos[n].dir = dir; g_pos[n].be = false;
   LogLine(StringFormat("open,NEWS,%s,%d,%.2f,%s,%s,%.0f,units %.0f dvol %.5f %s", sym, dir, lots,
                        DoubleToString(price, digits), DoubleToString(fill, digits), spread, units, dvol, tag));
   Notify(StringFormat("NEWS %s %s %.2f lots (%s)", dir > 0 ? "BUY" : "SELL", sym, lots, tag));
  }
void ManagePositions()
  {
   for(int i = ArraySize(g_pos) - 1; i >= 0; i--)
     {
      if(!PositionSelectByTicket(g_pos[i].ticket) || PositionGetInteger(POSITION_MAGIC) != InpMagicNews)
        { ArrayRemove(g_pos, i, 1); continue; }
      if(TimeCurrent() >= g_pos[i].opened + InpHoldMinutes * 60)
        { trade.PositionClose(g_pos[i].ticket); ArrayRemove(g_pos, i, 1); continue; }
      if(!g_pos[i].be)
        {
         double px = (g_pos[i].dir > 0) ? SymbolInfoDouble(g_pos[i].sym, SYMBOL_BID) : SymbolInfoDouble(g_pos[i].sym, SYMBOL_ASK);
         if(g_pos[i].dir * (px - g_pos[i].entry) >= g_pos[i].risk)
           {
            int digits = (int)SymbolInfoInteger(g_pos[i].sym, SYMBOL_DIGITS);
            if(trade.PositionModify(g_pos[i].ticket, NormalizeDouble(g_pos[i].entry, digits), 0)) g_pos[i].be = true;
           }
        }
     }
  }
void Execute(int kUsd, int kCad, string tag)
  {
   for(int i = 0; i < 6; i++)
     {
      int k = g_orient[i] * kUsd;
      if(i == 4) k = kUsd - kCad;
      if(k == 0 || g_skip[i]) continue;
      OpenNews(i, k > 0 ? 1 : -1, MathAbs(k), tag);
     }
  }
void ProcessCsv()
  {
   datetime now = TimeCurrent();
   while(g_evNext < ArraySize(g_evTime) && g_evTime[g_evNext] + InpDelayMinutes * 60 + 120 < now) g_evNext++;
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
bool IsDone(datetime t) { for(int i = 0; i < ArraySize(g_done); i++) if(g_done[i] == t) return true; return false; }
bool Inverse(string name)  { return (StringFind(name, "Unemployment Rate") >= 0 || StringFind(name, "Jobless Claims") >= 0); }
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
         if(!vals[i].HasActualValue() || !vals[i].HasForecastValue())
           { PrintFormat("release %s %s skipped: actual or forecast missing", curs[c], ev.name); continue; }
         double z = SurpriseZ(vals[i], ev);
         int j = -1;
         for(int q = 0; q < nt; q++) if(times[q] == t) j = q;
         if(j < 0) { ArrayResize(times, nt + 1); ArrayResize(kU, nt + 1); ArrayResize(kC, nt + 1); times[nt] = t; kU[nt] = 0; kC[nt] = 0; j = nt++; }
         PrintFormat("release %s %s actual=%.3f forecast=%.3f z=%.2f", curs[c], ev.name, vals[i].GetActualValue(), vals[i].GetForecastValue(), z);
         if(InpPushReleases && !(bool)MQLInfoInteger(MQL_TESTER))
            SendNotification(StringFormat("FTMO plan: %s %s a=%.2f f=%.2f z=%.2f %s", curs[c], ev.name, vals[i].GetActualValue(),
                             vals[i].GetForecastValue(), z, MathAbs(z) > InpZThreshold ? "-> counts" : "-> too small, no trade"));
         LogLine(StringFormat("release,NEWS,%s,,,,,,%s z=%.2f", curs[c], ev.name, z));
         if(MathAbs(z) > InpZThreshold) { if(c == 0) kU[j] += (z > 0 ? 1 : -1); else kC[j] += (z > 0 ? 1 : -1); }
        }
     }
   for(int q = 0; q < nt; q++)
     {
      int d = ArraySize(g_done); ArrayResize(g_done, d + 1); g_done[d] = times[q];
      if(kU[q] != 0 || kC[q] != 0) Execute(kU[q], kC[q], TimeToString(times[q], TIME_DATE | TIME_MINUTES));
     }
  }

//+------------------------------------------------------------------+
//  B) Nasdaq lunch-RSI
bool HasNasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t != 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNas) return true;
     }
   return false;
  }
void NasdaqStep()
  {
   datetime now = TimeCurrent();
   // flatten at 15:55 New York
   if(NYMinutes(now) >= 15 * 60 + 55 && HasNasPosition())
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong t = PositionGetTicket(i);
         if(t != 0 && PositionGetInteger(POSITION_MAGIC) == InpMagicNas) trade.PositionClose(t);
        }
      Notify("NASDAQ flat at 15:55 NY");
     }
   datetime bar0 = iTime(InpUS100, PERIOD_M15, 0);
   if(bar0 == 0 || bar0 == g_lastNasBar) return;          // act once, right after a 15m bar closes
   g_lastNasBar = bar0;
   datetime sigBar = iTime(InpUS100, PERIOD_M15, 1);
   int m = NYMinutes(sigBar);
   if(m < 11 * 60 + 30 || m >= 13 * 60 + 30) return;
   int dayKey = NYDayKey(sigBar);
   if(dayKey == g_nasTradedDay || HasNasPosition()) return;
   double rsi[1], atr[1];
   if(CopyBuffer(g_hRsi, 0, 1, 1, rsi) != 1 || CopyBuffer(g_hAtr, 0, 1, 1, atr) != 1) return;
   if(rsi[0] <= InpNasRsiLevel || atr[0] <= 0) return;
   double ask = SymbolInfoDouble(InpUS100, SYMBOL_ASK);
   double tv = SymbolInfoDouble(InpUS100, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(InpUS100, SYMBOL_TRADE_TICK_SIZE);
   if(ask <= 0 || tv <= 0 || ts <= 0) return;
   double stopDist = InpNasStopAtr * atr[0], tgtDist = InpNasTgtAtr * atr[0];
   double riskMoney = AccountInfoDouble(ACCOUNT_EQUITY) * InpNasRiskPct / 100.0 * SizeMult();
   double lots = NormLots(InpUS100, riskMoney / ((stopDist / ts) * tv));
   if(lots <= 0) { Print("NASDAQ skip: size too small"); return; }
   int digits = (int)SymbolInfoInteger(InpUS100, SYMBOL_DIGITS);
   double sl = NormalizeDouble(ask - stopDist, digits), tp = NormalizeDouble(ask + tgtDist, digits);
   trade.SetExpertMagicNumber(InpMagicNas);
   if(trade.Buy(lots, InpUS100, 0, sl, tp, "NASLUNCH"))
     {
      g_nasTradedDay = dayKey;
      LogLine(StringFormat("open,NASDAQ,%s,1,%.2f,%s,%s,%d,rsi %.1f atr %.2f", InpUS100, lots, DoubleToString(ask, digits),
                           DoubleToString(trade.ResultPrice(), digits), (int)SymbolInfoInteger(InpUS100, SYMBOL_SPREAD), rsi[0], atr[0]));
      Notify(StringFormat("NASDAQ BUY %.2f lots, SL %s TP %s", lots, DoubleToString(sl, digits), DoubleToString(tp, digits)));
     }
   else PrintFormat("NASDAQ order failed: %d", trade.ResultRetcode());
  }

//+------------------------------------------------------------------+
//  log every closing deal of this EA's strategies
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &req, const MqlTradeResult &res)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   long mg = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if(mg != InpMagicNews && mg != InpMagicNas) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_ENTRY) != DEAL_ENTRY_OUT) return;
   string sym = HistoryDealGetString(trans.deal, DEAL_SYMBOL);
   double pnl = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) + HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
                HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   LogLine(StringFormat("close,%s,%s,,%.2f,,%s,,pnl %.2f", mg == InpMagicNas ? "NASDAQ" : "NEWS", sym,
                        HistoryDealGetDouble(trans.deal, DEAL_VOLUME),
                        DoubleToString(HistoryDealGetDouble(trans.deal, DEAL_PRICE), digits), pnl));
  }
//+------------------------------------------------------------------+

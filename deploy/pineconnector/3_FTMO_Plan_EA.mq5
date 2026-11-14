//+------------------------------------------------------------------+
//|  FTMO_Plan_EA.mq5  v1.13                                         |
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
//  v1.13 SHADOW MODE: logs what 3 candidate exit ideas would have done. Trading is unchanged.
//  DATA: live/demo = MT5 economic calendar; Strategy Tester = news_events.csv (MQL5\Files).
//+------------------------------------------------------------------+
#property copyright "ETF-bot research"
#property version   "1.13"
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
input bool   InpUseTVCalendar = true;     // read TradingView's calendar (same source as the backtest). Allow WebRequest for https://economic-calendar.tradingview.com
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
input bool   InpShadow        = true;     // v1.13: record what the candidate exit ideas would have done (no trading effect)
input string InpShadowFile    = "ftmo_shadow.csv";

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
datetime g_tvDone[]; datetime g_tvLastPoll = 0; bool g_tvWarned = false;
// v1.12: surprise scale per release = std of (actual - forecast) over TradingView history 2015-2026 (same as the backtest)
string g_sdKey[] = {
   "CA|GDP Growth Rate Annualized",
   "CA|Inflation Rate YoY",
   "CA|Interest Rate",
   "CA|Ivey PMI s.a",
   "CA|Unemployment Rate",
   "US|Building Permits Prel",
   "US|Core Inflation Rate MoM",
   "US|Core Inflation Rate YoY",
   "US|Core PCE Price Index MoM",
   "US|Durable Goods Orders MoM",
   "US|Existing Home Sales",
   "US|GDP Growth Rate QoQ 2nd Est",
   "US|GDP Growth Rate QoQ Adv",
   "US|GDP Growth Rate QoQ Final",
   "US|Housing Starts",
   "US|ISM Manufacturing PMI",
   "US|ISM Services PMI",
   "US|Inflation Rate MoM",
   "US|Inflation Rate YoY",
   "US|JOLTs Job Openings",
   "US|Michigan Consumer Sentiment Prel",
   "US|Non Farm Payrolls",
   "US|PPI MoM",
   "US|Personal Income MoM",
   "US|Personal Spending MoM",
   "US|Retail Sales MoM",
   "US|Unemployment Rate"
};
double g_sdVal[] = { 2.28602, 0.197584, 0.083595, 5.58455, 0.434832, 0.0658545, 0.118319, 0.145804, 0.0680259, 2.05706, 0.143428, 0.255469, 0.887378, 0.21857, 0.0851814, 1.43448, 2.0732, 0.119649, 0.139459, 0.48094, 3.57679, 1670.4, 0.261461, 1.57016, 0.343479, 1.3097, 0.734341 };


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
   if(InpTradeNews && !UseCsv() && InpCalCheckDays > 0)
     {
      CalendarReport(InpCalCheckDays);
      if(InpUseTVCalendar) TVReport(InpCalCheckDays);
     }
   return INIT_SUCCEEDED;
  }
// v1.12 diagnostic: list recent high-impact USD/CAD releases with MT5's actual, forecast and our z-score
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
   if(InpTradeNews) { if(UseCsv()) ProcessCsv(); else if(InpUseTVCalendar) ProcessTV(); else ProcessCalendar(); }
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

//+------------------------------------------------------------------+
//  v1.12 TradingView calendar (same data as the backtest)
double SdFor(string country, string title)
  {
   string k = country + "|" + title;
   for(int i = 0; i < ArraySize(g_sdKey); i++) if(g_sdKey[i] == k) return g_sdVal[i];
   return 0.0;
  }
string JVal(string obj, string key)
  {
   int p = StringFind(obj, "\"" + key + "\":");
   if(p < 0) return "";
   p += StringLen(key) + 3;
   if(StringGetCharacter(obj, p) == '"')
     { int e = StringFind(obj, "\"", p + 1); return (e < 0) ? "" : StringSubstr(obj, p + 1, e - p - 1); }
   int e1 = StringFind(obj, ",", p), e2 = StringFind(obj, "}", p);
   int e = (e1 < 0) ? e2 : ((e2 < 0) ? e1 : MathMin(e1, e2));
   string v = (e < 0) ? StringSubstr(obj, p) : StringSubstr(obj, p, e - p);
   StringTrimLeft(v); StringTrimRight(v);
   return (v == "null") ? "" : v;
  }
datetime IsoToTime(string s)
  {
   string t = StringSubstr(s, 0, 19);
   StringReplace(t, "-", "."); StringReplace(t, "T", " ");
   return StringToTime(t);
  }
string IsoUTC(datetime u)
  {
   string d = TimeToString(u, TIME_DATE); StringReplace(d, ".", "-");
   return d + "T" + TimeToString(u, TIME_SECONDS) + ".000Z";
  }
bool TVFetch(datetime fromU, datetime toU, string &js)
  {
   string url = "https://economic-calendar.tradingview.com/events?from=" + IsoUTC(fromU) + "&to=" + IsoUTC(toU) + "&countries=US,CA";
   char post[], res[]; string hdr;
   ResetLastError();
   int code = WebRequest("GET", url, "Origin: https://www.tradingview.com\r\nUser-Agent: Mozilla/5.0\r\n", 5000, post, res, hdr);
   if(code != 200)
     {
      if(!g_tvWarned)
        {
         Notify(StringFormat("TV calendar failed (code %d, err %d). Allow WebRequest for https://economic-calendar.tradingview.com. Using MT5 calendar.",
                             code, GetLastError()));
         g_tvWarned = true;
        }
      return false;
     }
   js = CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8);
   return true;
  }
// read every usable release in the JSON; returns how many
int TVParse(string js, datetime &t[], string &cur[], string &name[], double &act[], double &fc[], double &z[])
  {
   int n = 0, p = StringFind(js, "\"id\":");
   while(p >= 0)
     {
      int q = StringFind(js, "\"id\":", p + 5);
      string o = (q < 0) ? StringSubstr(js, p) : StringSubstr(js, p, q - p);
      p = q;
      string imp = JVal(o, "importance"), ctry = JVal(o, "country"), title = JVal(o, "title");
      string a = JVal(o, "actual"), f = JVal(o, "forecast");
      if(imp != "1" || (ctry != "US" && ctry != "CA") || a == "" || f == "" || Excluded(title)) continue;
      StringReplace(title, ",", " ");
      double sd = SdFor(ctry, title);
      if(sd <= 0) { PrintFormat("TV release %s %s skipped: no history scale", ctry, title); continue; }
      double zz = (StringToDouble(a) - StringToDouble(f)) / sd;
      if(Inverse(title)) zz = -zz;
      ArrayResize(t, n + 1); ArrayResize(cur, n + 1); ArrayResize(name, n + 1); ArrayResize(act, n + 1); ArrayResize(fc, n + 1); ArrayResize(z, n + 1);
      t[n] = IsoToTime(JVal(o, "date")); cur[n] = (ctry == "US") ? "USD" : "CAD"; name[n] = title;
      act[n] = StringToDouble(a); fc[n] = StringToDouble(f); z[n] = zz; n++;
     }
   return n;
  }
bool TVIsDone(datetime t) { for(int i = 0; i < ArraySize(g_tvDone); i++) if(g_tvDone[i] == t) return true; return false; }
void ProcessTV()
  {
   datetime nowU = TimeGMT();
   MqlDateTime m; TimeToStruct(nowU, m);
   int mm = m.min % 15;
   if(mm < InpDelayMinutes || mm > InpDelayMinutes + 2) return;      // releases land on :00/:15/:30/:45
   if(nowU - g_tvLastPoll < 20) return;
   g_tvLastPoll = nowU;
   string js;
   if(!TVFetch(nowU - 45 * 60, nowU, js)) { ProcessCalendar(); return; }
   datetime t[]; string cur[], name[]; double act[], fc[], z[];
   int n = TVParse(js, t, cur, name, act, fc, z);
   datetime times[]; int kU[], kC[]; int nt = 0;
   for(int i = 0; i < n; i++)
     {
      if(nowU < t[i] + InpDelayMinutes * 60 || nowU > t[i] + InpDelayMinutes * 60 + 150 || TVIsDone(t[i])) continue;
      int j = -1;
      for(int q = 0; q < nt; q++) if(times[q] == t[i]) j = q;
      if(j < 0) { ArrayResize(times, nt + 1); ArrayResize(kU, nt + 1); ArrayResize(kC, nt + 1); times[nt] = t[i]; kU[nt] = 0; kC[nt] = 0; j = nt++; }
      PrintFormat("release (TV) %s %s actual=%.3f forecast=%.3f z=%.2f", cur[i], name[i], act[i], fc[i], z[i]);
      LogLine(StringFormat("release,NEWS,%s,,,,,,%s z=%.2f (TV)", cur[i], name[i], z[i]));
      if(InpPushReleases && !(bool)MQLInfoInteger(MQL_TESTER))
         SendNotification(StringFormat("FTMO plan: %s %s a=%.2f f=%.2f z=%.2f %s", cur[i], name[i], act[i], fc[i], z[i],
                          MathAbs(z[i]) > InpZThreshold ? "-> counts" : "-> too small, no trade"));
      if(MathAbs(z[i]) > InpZThreshold) { if(cur[i] == "USD") kU[j] += (z[i] > 0 ? 1 : -1); else kC[j] += (z[i] > 0 ? 1 : -1); }
     }
   for(int q = 0; q < nt; q++)
     {
      int d = ArraySize(g_tvDone); ArrayResize(g_tvDone, d + 1); g_tvDone[d] = times[q];
      if(kU[q] != 0 || kC[q] != 0) Execute(kU[q], kC[q], TimeToString(times[q], TIME_DATE | TIME_MINUTES) + " UTC (TV)");
     }
  }
void TVReport(int days)
  {
   string js;
   if(!TVFetch(TimeGMT() - days * 86400, TimeGMT(), js)) return;
   datetime t[]; string cur[], name[]; double act[], fc[], z[];
   int n = TVParse(js, t, cur, name, act, fc, z), big = 0; string summary = "";
   for(int i = 0; i < n; i++)
     {
      if(MathAbs(z[i]) > InpZThreshold) big++;
      PrintFormat("CALCHECK-TV %s %s UTC | %s | actual=%.3f forecast=%.3f z=%.2f%s", cur[i], TimeToString(t[i]), name[i], act[i], fc[i], z[i],
                  MathAbs(z[i]) > InpZThreshold ? "  <-- would trade" : "");
      if(StringFind(name[i], "Inflation Rate MoM") >= 0 && StringLen(summary) < 150)
         summary += StringFormat(" %s a%.1f f%.1f z%.1f;", name[i], act[i], fc[i], z[i]);
     }
   Notify(StringFormat("TradingView calendar OK: %d releases in %dd, %d above z %.1f.%s", n, days, big, InpZThreshold, summary));
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
//  v1.13 SHADOW MODE - records what 3 candidate ideas WOULD have done.
//  It never opens, closes or changes a trade. One "SHADOW" line per Nasdaq trade in the Experts log
//  (+ raw numbers in InpShadowFile). Models trained on 2016-20 in results/daytrade/2026-11-14.
//   trail     : trail 1R below the high once +1.5R reached (completed M15 bars)
//   reassure  : entry model says weak -> use trail, strong -> hold as now
//   smart     : at the first +0.8R bar, logistic model; p < 0.5 -> close at +0.8R
//   weekstop  : skip the trade if this week's Nasdaq result is already >= +2R
struct NasShadow
  {
   bool     active;
   datetime entryBar, lastBar;
   double   e, s0, tg, R, riskMoney;
   double   rsiEntry, dayRet, preRet, vol20, stopPct;
   double   logitReassure; bool weak;
   bool     smartDone, hasDecision; double smartP;
   double   trailStop, hi; bool trailOut; double trailGross;
   int      nbars;
   bool     weekSkip;
   string   feat;
  };
NasShadow g_sh;

double RS_MEAN[6]  = {1.14132, 3.698082, 8.20021, 0.813434, 74.822492, 31.484099};
double RS_SCALE[6] = {0.318275, 1.13526, 10.789094, 5.237823, 4.351323, 29.723501};
double RS_COEF[6]  = {-0.190852, -0.340189, 0.046984, -0.133004, 0.279707, -0.120408};
double RS_ICPT = -1.420447;
double RS_THR  = -1.418716;
double SM_MEAN[9]  = {2.077381, 754.375, 0.188207, 74.781697, 0.694173, 0.374894, 0.114627, 0.077262, 1.112769};
double SM_SCALE[9] = {2.901143, 61.550375, 0.092982, 4.413004, 0.384638, 0.300764, 0.058109, 0.450247, 0.45687};
double SM_COEF[9]  = {-0.37655, 0.197862, 0.179035, 0.085431, 0.056815, -0.04748, 0.012537, 0.353262, -0.09367};
double SM_ICPT = 0.452823;
#define SH_WK "FTMO_SHADOW_WEEK"
#define SH_WR "FTMO_SHADOW_WEEKR"

int UTCWeekKey(datetime srv)
  {
   datetime u = ServerToUTC(srv);
   MqlDateTime d; TimeToStruct(u, d);
   datetime mon = u - ((d.day_of_week + 6) % 7) * 86400;
   TimeToStruct(mon, d);
   return d.year * 10000 + d.mon * 100 + d.day;
  }

void ShadowReset()
  {
   g_sh.active = false; g_sh.entryBar = 0; g_sh.lastBar = 0; g_sh.e = 0; g_sh.s0 = 0; g_sh.tg = 0; g_sh.R = 0; g_sh.riskMoney = 0;
   g_sh.rsiEntry = 0; g_sh.dayRet = 0; g_sh.preRet = 0; g_sh.vol20 = 0; g_sh.stopPct = 0;
   g_sh.logitReassure = 0; g_sh.weak = false; g_sh.smartDone = false; g_sh.hasDecision = false; g_sh.smartP = 0;
   g_sh.trailStop = 0; g_sh.hi = 0; g_sh.trailOut = false; g_sh.trailGross = 0; g_sh.nbars = 0; g_sh.weekSkip = false; g_sh.feat = "";
  }

// called right after a Nasdaq buy fills. fill = entry price, sl/tp as sent, rsiSig = signal-bar RSI
void ShadowOpen(double fill, double sl, double tp, double lots, double rsiSig)
  {
   ShadowReset();
   MqlRates r[]; ArraySetAsSeries(r, true);
   int n = CopyRates(InpUS100, PERIOD_M15, 0, 2200, r);        // r[0] = forming entry bar
   if(n < 600 || fill - sl <= 0) { Print("SHADOW: not enough history - this trade not recorded"); return; }
   double tv = SymbolInfoDouble(InpUS100, SYMBOL_TRADE_TICK_VALUE), ts = SymbolInfoDouble(InpUS100, SYMBOL_TRADE_TICK_SIZE);
   g_sh.e = fill; g_sh.s0 = sl; g_sh.tg = tp; g_sh.R = fill - sl;
   g_sh.riskMoney = lots * (g_sh.R / ts) * tv;
   g_sh.entryBar = r[0].time; g_sh.lastBar = 0; g_sh.nbars = 0;
   g_sh.trailStop = sl; g_sh.hi = -DBL_MAX;
   // range ratio: mean(H-L) of the 26 bars before entry / of the 520 bars before entry
   double a26 = 0, a520 = 0;
   for(int i = 1; i <= 520; i++) { double rg = r[i].high - r[i].low; a520 += rg; if(i <= 26) a26 += rg; }
   double volRatio = (a26 / 26) / (a520 / 520);
   // NY session: today's 09:30 open and each NY day's last close (bar starting 09:30-15:59)
   int today = NYDayKey(r[0].time);
   double open930 = 0; int dkeys[]; double dclose[]; int nd = 0;
   for(int i = 0; i < n; i++)
     {
      int m = NYMinutes(r[i].time), dk = NYDayKey(r[i].time);
      if(dk == today && m == 570) open930 = r[i].open;
      if(m >= 570 && m < 960)
        {
         if(nd == 0 || dkeys[nd - 1] != dk)
           { if(nd >= 8) break; ArrayResize(dkeys, nd + 1); ArrayResize(dclose, nd + 1); dkeys[nd] = dk; dclose[nd] = r[i].close; nd++; }
        }
     }
   // dkeys[0] = today (latest close so far), [1] = yesterday ... (newest first)
   if(open930 <= 0 || nd < 6 || dkeys[0] != today) { Print("SHADOW: session data missing - this trade not recorded"); return; }
   double R = g_sh.R;
   double x[6];
   x[0] = volRatio;
   x[1] = (fill - open930) / R;
   x[2] = (fill - dclose[5]) / R;
   x[3] = (dclose[1] - dclose[2]) / R;
   x[4] = rsiSig;
   x[5] = NYMinutes(r[0].time) - 690;
   double z = RS_ICPT;
   for(int k = 0; k < 6; k++) z += RS_COEF[k] * (x[k] - RS_MEAN[k]) / RS_SCALE[k];
   g_sh.logitReassure = z; g_sh.weak = (z < RS_THR);
   // smart-exit entry features
   g_sh.rsiEntry = rsiSig;
   g_sh.dayRet = (fill / open930 - 1) * 100;
   g_sh.preRet = (r[1].close / r[5].close - 1) * 100;
   double pc[20], mu = 0;
   for(int j = 0; j < 20; j++) { pc[j] = r[1 + j].close / r[2 + j].close - 1; mu += pc[j]; }
   mu /= 20; double v = 0; for(int j = 0; j < 20; j++) v += (pc[j] - mu) * (pc[j] - mu);
   g_sh.vol20 = MathSqrt(v / 19) * 100;
   g_sh.stopPct = R / fill * 100;
   // weekly stop: shadow week result so far
   int wk = UTCWeekKey(TimeCurrent());
   if(!GlobalVariableCheck(SH_WK) || (int)GlobalVariableGet(SH_WK) != wk) { GlobalVariableSet(SH_WK, wk); GlobalVariableSet(SH_WR, 0); }
   g_sh.weekSkip = (GlobalVariableGet(SH_WR) >= 2.0);
   g_sh.feat = StringFormat("volr %.3f daymv %.3f wk %.3f prev %.3f rsi %.2f mins %d", x[0], x[1], x[2], x[3], x[4], (int)x[5]);
   g_sh.active = true;
  }

// one bar of the trade (completed, or the forming bar at close time when partial=true)
void ShadowBar(datetime t, double o, double h, double l, double c, bool partial)
  {
   double e = g_sh.e, R = g_sh.R;
   if(!g_sh.trailOut)
     {
      if(l <= g_sh.trailStop) { g_sh.trailOut = true; g_sh.trailGross = ((t > g_sh.entryBar ? MathMin(o, g_sh.trailStop) : g_sh.trailStop) - e) / R; }
      else if(h >= g_sh.tg) { g_sh.trailOut = true; g_sh.trailGross = (g_sh.tg - e) / R; }
      else if(!partial)
        {
         g_sh.hi = MathMax(g_sh.hi, h);
         if(g_sh.hi >= e + 1.5 * R) g_sh.trailStop = MathMax(g_sh.trailStop, g_sh.hi - R);
        }
     }
   if(!g_sh.smartDone && !partial)
     {
      if(l <= g_sh.s0) g_sh.smartDone = true;
      else if(h >= e + 0.8 * R)
        {
         double atr[1]; int sh = iBarShift(InpUS100, PERIOD_M15, t, true);
         double atrv = (sh >= 0 && CopyBuffer(g_hAtr, 0, sh, 1, atr) == 1) ? atr[0] : 0;
         double x[9];
         x[0] = g_sh.nbars; x[1] = NYMinutes(t); x[2] = g_sh.stopPct; x[3] = g_sh.rsiEntry; x[4] = g_sh.dayRet;
         x[5] = g_sh.preRet; x[6] = g_sh.vol20; x[7] = (c - e) / R - 0.8; x[8] = atrv > 0 ? (h - l) / atrv : 1.0;
         double z = SM_ICPT;
         for(int k = 0; k < 9; k++) z += SM_COEF[k] * (x[k] - SM_MEAN[k]) / SM_SCALE[k];
         g_sh.smartP = 1.0 / (1.0 + MathExp(-z));
         g_sh.smartDone = true; g_sh.hasDecision = true;
         PrintFormat("SHADOW note: +0.8R reached, smart-exit says %s (p=%.2f)", g_sh.smartP < 0.5 ? "CLOSE" : "HOLD", g_sh.smartP);
        }
     }
   if(!partial) { g_sh.lastBar = t; g_sh.nbars++; }
  }

// process completed bars not yet seen (from the entry bar on)
void ShadowCatchUp()
  {
   if(!g_sh.active) return;
   int sh = iBarShift(InpUS100, PERIOD_M15, g_sh.entryBar, false);
   for(int i = sh; i >= 1; i--)
     {
      datetime t = iTime(InpUS100, PERIOD_M15, i);
      if(t < g_sh.entryBar || t <= g_sh.lastBar) continue;
      ShadowBar(t, iOpen(InpUS100, PERIOD_M15, i), iHigh(InpUS100, PERIOD_M15, i), iLow(InpUS100, PERIOD_M15, i), iClose(InpUS100, PERIOD_M15, i), false);
     }
  }

void ShadowClose(double pnl, double exitPrice)
  {
   if(!g_sh.active) { Print("SHADOW: trade closed but not recorded (EA restarted during the trade)"); return; }
   ShadowCatchUp();
   ShadowBar(iTime(InpUS100, PERIOD_M15, 0), iOpen(InpUS100, PERIOD_M15, 0), iHigh(InpUS100, PERIOD_M15, 0), iLow(InpUS100, PERIOD_M15, 0), 0, true);
   double actual = g_sh.riskMoney > 0 ? pnl / g_sh.riskMoney : 0;
   double cost = (exitPrice - g_sh.e) / g_sh.R - actual;                  // costs in R (spread, commission, swap)
   double trail = g_sh.trailOut ? g_sh.trailGross - cost : actual;
   double reass = g_sh.weak ? trail : actual;
   bool smartClose = g_sh.hasDecision && g_sh.smartP < 0.5;
   double smart = smartClose ? 0.8 - cost : actual;
   double week = g_sh.weekSkip ? 0 : actual;
   GlobalVariableSet(SH_WR, GlobalVariableGet(SH_WR) + week);
   string d = TimeToString(g_sh.entryBar, TIME_DATE);
   PrintFormat("SHADOW %s | actual %+.2fR | trail %+.2fR | entry %s %+.2fR | smart %s %+.2fR | weekstop %s %+.2fR",
               d, actual, trail, g_sh.weak ? "WEAK" : "STRONG", reass,
               !g_sh.hasDecision ? "n/a" : (smartClose ? "CLOSE" : "HOLD"), smart, g_sh.weekSkip ? "SKIP" : "ok", week);
   int h = FileOpen(InpShadowFile, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h != INVALID_HANDLE)
     {
      if(FileSize(h) == 0) FileWriteString(h, "entry_bar,entry,stop,target,actualR,costR,trailR,reassure_logit,weak,smart_p,smart_close,week_skip,features\r\n");
      FileSeek(h, 0, SEEK_END);
      FileWriteString(h, StringFormat("%s,%.2f,%.2f,%.2f,%.3f,%.3f,%.3f,%.4f,%d,%.4f,%d,%d,%s\r\n", TimeToString(g_sh.entryBar), g_sh.e, g_sh.s0, g_sh.tg,
                                      actual, cost, trail, g_sh.logitReassure, (int)g_sh.weak, g_sh.hasDecision ? g_sh.smartP : -1.0, (int)smartClose, (int)g_sh.weekSkip, g_sh.feat));
      FileClose(h);
     }
   g_sh.active = false;
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
   if(InpShadow && g_sh.active) ShadowCatchUp();
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
      if(InpShadow) ShadowOpen(trade.ResultPrice() > 0 ? trade.ResultPrice() : ask, sl, tp, lots, rsi[0]);
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
   if(InpShadow && mg == InpMagicNas) ShadowClose(pnl, HistoryDealGetDouble(trans.deal, DEAL_PRICE));
  }
//+------------------------------------------------------------------+

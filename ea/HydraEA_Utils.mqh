//+------------------------------------------------------------------+
//|                                                  HydraEA_Utils.mqh|
//|                                          Hydra Trading System v1.0|
//|                                            Utility Helper Library|
//+------------------------------------------------------------------+
// Renamed from HERMES → Hydra for standalone copy-trade distribution
//
// Shared utility functions used by HydraCopyEA and related EAs.
// Includes JSON parsing helpers, risk calculation, and market tools.
//+------------------------------------------------------------------+
#property copyright "Hydra Trading System"
#property version   "1.00"

//+------------------------------------------------------------------+
//| String Utilities                                                 |
//+------------------------------------------------------------------+
string HydraStrTrim(const string &str) {
   string result = str;
   while (StringLen(result) > 0 && StringGetChar(result, 0) <= 32)
      result = StringSubstr(result, 1);
   while (StringLen(result) > 0 && StringGetChar(result, StringLen(result)-1) <= 32)
      result = StringSubstr(result, 0, StringLen(result)-1);
   return result;
}

string HydraStrBetween(const string &str, const string &start, const string &end) {
   int pos1 = StringFind(str, start);
   if (pos1 < 0) return "";
   pos1 += StringLen(start);

   int pos2 = StringFind(str, end, pos1);
   if (pos2 < 0) return "";

   return StringSubstr(str, pos1, pos2 - pos1);
}

//+------------------------------------------------------------------+
//| Symbol Helpers                                                   |
//+------------------------------------------------------------------+
double HydraGetPointValue(const string symbol) {
   return SymbolInfoDouble(symbol, SYMBOL_POINT);
}

double HydraGetTickValue(const string symbol) {
   return SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
}

double HydraGetMinLot(const string symbol) {
   return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
}

double HydraGetMaxLot(const string symbol) {
   return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
}

double HydraGetLotStep(const string symbol) {
   return SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
}

//+------------------------------------------------------------------+
//| Risk Calculation Helper                                          |
//+------------------------------------------------------------------+
double HydraCalculateLotFromRisk(
   const string symbol,
   double risk_percent,
   double sl_price,
   double lot_multiplier = 1.0,
   double max_lot_cap = 5.0
) {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_amount = equity * risk_percent / 100.0;

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double sl_distance = MathAbs(bid - sl_price);

   if (sl_distance <= 0) return HydraGetMinLot(symbol);

   double tick_value = HydraGetTickValue(symbol);
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   double lot = risk_amount / ((sl_distance / tick_size) * tick_value);

   // Apply multiplier and cap
   lot *= lot_multiplier;
   lot = MathMin(lot, max_lot_cap);

   // Normalize to lot step
   double lot_step = HydraGetLotStep(symbol);
   lot = MathFloor(lot / lot_step) * lot_step;
   lot = MathMax(lot, HydraGetMinLot(symbol));
   lot = MathMin(lot, HydraGetMaxLot(symbol));

   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Position Scanner                                                 |
//+------------------------------------------------------------------+
int HydraCountOpenPositions(ulong magic_number) {
   int count = 0;
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (PositionSelectByTicket(ticket)) {
         if (PositionGetInteger(POSITION_MAGIC) == magic_number) {
            count++;
         }
      }
   }
   return count;
}

double HydraCalculateTotalProfit(ulong magic_number) {
   double total = 0;
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (PositionSelectByTicket(ticket)) {
         if (PositionGetInteger(POSITION_MAGIC) == magic_number) {
            total += PositionGetDouble(POSITION_PROFIT);
         }
      }
   }
   return total;
}

//+------------------------------------------------------------------+
//| Trade Confirmation Helpers                                       |
//+------------------------------------------------------------------+
string HydraFormatTradeConfirmation(
   string signal_id,
   ulong account,
   string symbol,
   string type,
   double lot,
   double fill_price,
   double sl_price,
   double tp_price,
   ulong ticket
) {
   return StringFormat(
      "✅ TRADE CONFIRMED [HYDRA]\n"
      "Signal: %%s\n"
      "Account: %%I64d\n"
      "Symbol: %%s\n"
      "Type: %%s\n"
      "Lot: %%.2f\n"
      "Fill: %%.5f\n"
      "SL: %%.5f\n"
      "TP: %%.5f\n"
      "Ticket: %%I64d",
      signal_id, account, symbol, type, lot, fill_price, sl_price, tp_price, ticket
   );
}

//+------------------------------------------------------------------+
//| News Filter Helper                                               |
//+------------------------------------------------------------------+
bool HydraIsNewsTime() {
   // Simple check: avoid trading 30 min before/after major news
   // In production: fetch economic calendar via API

   MqlDateTime dt;
   TimeCurrent(dt);

   // Skip weekends
   if (dt.day_of_week == 0 || dt.day_of_week == 6) return true;

   // Skip major news hours (placeholder — extend with actual calendar)
   // Friday non-farm payroll, FOMC, etc.
   if (dt.day_of_week == 5 && dt.hour >= 12 && dt.hour <= 14) return true;

   return false;
}

//+------------------------------------------------------------------+
//|                                                 HydraClientEA.mq5|
//|                                          Hydra Trading System v2.0|
//|                          Client EA with Dynamic Money Management  |
//+------------------------------------------------------------------+
// Renamed from HERMES → Hydra for standalone copy-trade distribution
// Source: Qwen Architecture Proposal 2026-06-02 — Master EA + Client EA
//
// Client-side EA with:
//  - Dynamic Money Management (equity-based lot sizing, % trade by equity)
//  - Smart Pending Order Management (margin checks, expiry, reserve)
//  - Multi-Layer Risk Protection (daily loss, drawdown, margin level)
//  - USD + USC Cent account support via Currency Factor
//  - Signal reception from Telegram Bot
//+------------------------------------------------------------------+
#property copyright "Hydra Trading System"
#property version   "2.00"
#property strict
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//| INPUT PARAMETERS — Money Management                              |
//+------------------------------------------------------------------+
input group "=== 💰 Money Management ==="
input double   InpTradeByEquityPct = 50.0;     // % of available equity to trade
input double   InpMaxRiskPerTrade  = 2.0;      // Max Risk % per trade
input double   InpMaxLotCap        = 10.0;     // Max lot allowed
input double   InpMinLotFloor      = 0.01;     // Min lot floor

input group "=== 📊 Account Type ==="
input double   InpCurrencyFactor   = 1.0;      // 1.0 (USD→USD), 100.0 (USD→USC)

input group "=== 🛡️ Risk Management ==="
input double   InpMaxDailyLoss     = 5.0;      // Max Daily Loss %
input double   InpMaxDrawdown      = 15.0;     // Max Drawdown %
input int      InpMaxOpenOrders    = 10;       // Max open positions
input int      InpMaxPendingOrders = 5;        // Max pending orders
input double   InpMinMarginLevel   = 200.0;    // Min Margin Level %

input group "=== ⚙️ Pending Orders ==="
input bool     InpSmartPendingMgmt = true;     // Smart Pending Management
input int      InpPendingExpiry    = 30;       // Pending order expiry (min)
input double   InpPendingMarginReserve = 20.0; // Margin reserve for pending %

input group "=== 🎯 Execution ==="
input ulong    InpMagicNumber      = 20260527; // Magic Number
input int      InpSlippage         = 30;       // Slippage (points)
input bool     InpAutoExecute      = true;     // Auto-execute trades

input group "=== 🔗 Connection ==="
input string   InpBotToken         = "YOUR_BOT_TOKEN";
input ulong    InpMasterChatID     = 0;        // Master Chat ID
input string   InpMyChatID         = "";        // Own Chat ID

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
CTrade         trade;
CSymbolInfo    symbolInfo;

struct PendingSignal {
   string        signal_id;
   string        symbol;
   ENUM_ORDER_TYPE direction;
   double        entry_price;
   double        sl_price;
   double        tp1, tp2, tp3;
   double        risk_percent;
   double        lot_multiplier;
   string        source;
   int           grid_layer;
   datetime      timestamp;
   int           expiry_minutes;
   bool          processed;
   ulong         ticket;
};

PendingSignal  signal_queue[];
int            signal_count = 0;

double         start_equity = 0;
double         daily_start_equity = 0;
datetime       last_reset_time = 0;

//+------------------------------------------------------------------+
//| INITIALIZATION                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   daily_start_equity = start_equity;
   last_reset_time = TimeCurrent();

   Print("🎯 Hydra Client EA initialized");
   Print("💰 Account: ", AccountInfoInteger(ACCOUNT_LOGIN));
   Print("💵 Balance: ", AccountInfoDouble(ACCOUNT_BALANCE), " ", AccountInfoString(ACCOUNT_CURRENCY));
   Print("📊 Equity: ", AccountInfoDouble(ACCOUNT_EQUITY));
   Print("⚙️ Trade by Equity: ", InpTradeByEquityPct, "%");
   Print("⚙️ Currency Factor: ", InpCurrencyFactor);

   SendRegistrationToMaster();

   EventSetTimer(10);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   EventKillTimer();
}

//+------------------------------------------------------------------+
//| MAIN TICK FUNCTION                                               |
//+------------------------------------------------------------------+
void OnTick() {
   CheckDailyReset();
   if(!CheckRiskLimits()) {
      Print("🚨 Risk limit breached. No new trades.");
      return;
   }
   if(InpAutoExecute) ProcessSignalQueue();
   ManageOpenPositions();
   if(InpSmartPendingMgmt) ManagePendingOrders();
}

void OnTimer() {
   FetchNewSignalsFromTelegram();
}

//+------------------------------------------------------------------+
//| DYNAMIC MONEY MANAGEMENT                                         |
//+------------------------------------------------------------------+
double CalculateDynamicLotSize(double risk_percent, double sl_price, double entry_price) {
   // 1. Available Equity = Total Equity - Used Margin
   double total_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double used_margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double available_equity = total_equity - used_margin;

   // 2. Trade Equity = Available × User_Percent%
   double trade_equity = available_equity * (InpTradeByEquityPct / 100.0);

   // 3. Risk Amount
   double risk_amount = trade_equity * (risk_percent / 100.0);

   // 4. SL Distance
   double sl_distance = MathAbs(entry_price - sl_price);
   if(sl_distance <= 0) return InpMinLotFloor;

   // 5. Tick Value / Size
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_value <= 0 || tick_size <= 0) return InpMinLotFloor;

   // 6. Base Lot Size
   double lot = risk_amount / ((sl_distance / tick_size) * tick_value);

   // 7. Apply Currency Factor (USD ↔ USC conversion)
   lot = lot * InpCurrencyFactor;

   // 8. Normalize to lot step
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathFloor(lot / lot_step) * lot_step;

   // 9. Apply Min/Max constraints
   lot = MathMax(lot, InpMinLotFloor);
   lot = MathMin(lot, InpMaxLotCap);
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));

   // 10. Check Margin Sufficiency — auto-reduce if needed
   double required_margin = CalculateRequiredMargin(lot);
   if(required_margin > available_equity) {
      Print("⚠️ Insufficient margin. Required: ", required_margin,
            " Available: ", available_equity);
      lot = lot * (available_equity / required_margin) * 0.95;
      lot = MathFloor(lot / lot_step) * lot_step;
      lot = MathMax(lot, InpMinLotFloor);
   }

   Print("💰 Dynamic Lot Calc: AvailEq=", available_equity,
         " TradeEq=", trade_equity, " RiskAmt=", risk_amount,
         " Lot=", lot);
   return NormalizeDouble(lot, 2);
}

double CalculateRequiredMargin(double lot) {
   double margin_rate = SymbolInfoDouble(_Symbol, SYMBOL_MARGIN_INITIAL);
   double contract_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double current_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double leverage = AccountInfoInteger(ACCOUNT_LEVERAGE);
   if(leverage <= 0) leverage = 500;
   double margin = (lot * contract_size * current_price * margin_rate) / leverage;
   return margin;
}

//+------------------------------------------------------------------+
//| SIGNAL PROCESSING                                                |
//+------------------------------------------------------------------+
void ProcessSignalQueue() {
   for(int i = 0; i < signal_count; i++) {
      if(signal_queue[i].processed) continue;

      datetime expiry_time = signal_queue[i].timestamp + signal_queue[i].expiry_minutes * 60;
      if(TimeCurrent() > expiry_time) {
         Print("⏰ Signal expired: ", signal_queue[i].signal_id);
         signal_queue[i].processed = true;
         continue;
      }
      if(ExecuteSignal(signal_queue[i])) {
         signal_queue[i].processed = true;
         Print("✅ Signal executed: ", signal_queue[i].signal_id);
      }
   }
}

bool ExecuteSignal(PendingSignal &sig) {
   if(sig.symbol != _Symbol) return false;

   symbolInfo.Name(_Symbol);
   symbolInfo.RefreshRates();

   // 1. Dynamic Lot Size
   double lot = CalculateDynamicLotSize(sig.risk_percent, sig.sl_price, sig.entry_price);
   if(lot <= 0) { Print("❌ Invalid lot size"); return false; }

   // 2. Spread Filter
   double spread = symbolInfo.Spread() * _Point;
   double max_spread = symbolInfo.Ask() * 0.002;
   if(spread > max_spread) { Print("⚠️ Spread too high"); return false; }

   // 3. Slippage Check
   double current_price = (sig.direction == ORDER_TYPE_BUY) ?
                           symbolInfo.Ask() : symbolInfo.Bid();
   double slippage_points = MathAbs(current_price - sig.entry_price) / _Point;
   if(slippage_points > InpSlippage) { Print("⚠️ Slippage too high"); return false; }

   // 4. Max Open Orders Check
   if(CountOpenPositions() >= InpMaxOpenOrders) { Print("⚠️ Max orders reached"); return false; }

   // 5. Execute
   bool result = false;
   if(sig.direction == ORDER_TYPE_BUY) {
      result = trade.Buy(lot, _Symbol, 0, sig.sl_price, sig.tp1,
                         "HYDRA_" + sig.signal_id);
   } else {
      result = trade.Sell(lot, _Symbol, 0, sig.sl_price, sig.tp1,
                          "HYDRA_" + sig.signal_id);
   }

   if(result) {
      sig.ticket = trade.ResultOrder();
      Print("📍 Order placed: Ticket=", sig.ticket, " Lot=", lot);
      SendTradeConfirmation(sig, lot, current_price);
      return true;
   } else {
      Print("❌ Order failed: ", trade.ResultRetcodeDescription());
      return false;
   }
}

//+------------------------------------------------------------------+
//| PENDING ORDER MANAGEMENT (Smart)                                 |
//+------------------------------------------------------------------+
void ManagePendingOrders() {
   int pending_count = CountPendingOrders();
   if(pending_count >= InpMaxPendingOrders) return;

   double total_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double used_margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double available_equity = total_equity - used_margin;
   double reserve_for_pending = total_equity * (InpPendingMarginReserve / 100.0);
   double usable_for_pending = available_equity - reserve_for_pending;
   if(usable_for_pending <= 0) return;

   CleanupExpiredPendingOrders();

   for(int i = 0; i < signal_count; i++) {
      if(signal_queue[i].processed) continue;
      if(signal_queue[i].ticket != 0) continue;

      double pending_lot = CalculateDynamicLotSize(
         signal_queue[i].risk_percent, signal_queue[i].sl_price, signal_queue[i].entry_price);
      double pending_margin = CalculateRequiredMargin(pending_lot);

      if(pending_margin > usable_for_pending) continue;

      if(PlacePendingOrder(signal_queue[i], pending_lot)) {
         usable_for_pending -= pending_margin;
         signal_queue[i].processed = true;
      }
   }
}

bool PlacePendingOrder(PendingSignal &sig, double lot) {
   symbolInfo.Name(sig.symbol);
   symbolInfo.RefreshRates();

   double current_price = (sig.direction == ORDER_TYPE_BUY) ?
                           symbolInfo.Ask() : symbolInfo.Bid();
   double distance = MathAbs(sig.entry_price - current_price);

   if(distance < 10 * _Point) {
      Print("📍 Price close to entry, Market Order instead");
      sig.entry_price = current_price;
      return ExecuteSignal(sig);
   }

   bool result = false;
   if(sig.direction == ORDER_TYPE_BUY) {
      result = trade.BuyLimit(lot, sig.entry_price, _Symbol, sig.sl_price, sig.tp1,
                              ORDER_TIME_GTC, 0, "HYDRA_PEND_" + sig.signal_id);
   } else {
      result = trade.SellLimit(lot, sig.entry_price, _Symbol, sig.sl_price, sig.tp1,
                               ORDER_TIME_GTC, 0, "HYDRA_PEND_" + sig.signal_id);
   }
   if(result) {
      sig.ticket = trade.ResultOrder();
      Print("📍 Pending order placed: Ticket=", sig.ticket, " Price=", sig.entry_price);
      return true;
   }
   return false;
}

void CleanupExpiredPendingOrders() {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      string comment = PositionGetString(POSITION_COMMENT);
      if(StringFind(comment, "HYDRA_PEND_") == 0) {
         datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent() - open_time > InpPendingExpiry * 60) {
            Print("⏰ Pending expired, cancelling: ", ticket);
            trade.OrderDelete(ticket);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| RISK MANAGEMENT                                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   double daily_loss_pct = ((daily_start_equity - equity) / daily_start_equity) * 100;
   if(daily_loss_pct >= InpMaxDailyLoss) {
      Print("🚨 Daily loss limit: ", daily_loss_pct, "%");
      return false;
   }

   double dd_pct = ((start_equity - equity) / start_equity) * 100;
   if(dd_pct >= InpMaxDrawdown) {
      Print("🚨 Max drawdown! Closing all.");
      CloseAllPositions();
      return false;
   }

   double margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   if(margin_level > 0 && margin_level < InpMinMarginLevel) {
      Print("🚨 Margin level low: ", margin_level, "%");
      return false;
   }
   return true;
}

void CheckDailyReset() {
   MqlDateTime dt;
   TimeCurrent(dt);
   MqlDateTime last_dt;
   TimeToStruct(last_reset_time, last_dt);
   if(dt.day != last_dt.day) {
      daily_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      last_reset_time = TimeCurrent();
      Print("🔄 Daily reset. New start equity: ", daily_start_equity);
   }
}

void CloseAllPositions() {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) {
         trade.PositionClose(ticket);
      }
   }
}

//+------------------------------------------------------------------+
//| HELPERS                                                          |
//+------------------------------------------------------------------+
int CountOpenPositions() {
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++) {
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) count++;
   }
   return count;
}

int CountPendingOrders() {
   int count = 0;
   for(int i = 0; i < OrdersTotal(); i++) {
      ulong ticket = OrderGetTicket(i);
      if(OrderGetInteger(ORDER_MAGIC) == InpMagicNumber) count++;
   }
   return count;
}

void ManageOpenPositions() {
   // Trailing stop, partial close — extend per strategy
}

//+------------------------------------------------------------------+
//| TELEGRAM COMMUNICATION                                           |
//+------------------------------------------------------------------+
void FetchNewSignalsFromTelegram() {
   // Poll Telegram Bot API for new signals.
   // Parse JSON from <blockquote> and add to signal_queue.
}

void SendRegistrationToMaster() {
   string msg = "🆕 CLIENT REGISTERED [HYDRA]\n";
   msg += "Account: " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\n";
   msg += "Currency: " + AccountInfoString(ACCOUNT_CURRENCY) + "\n";
   msg += "Balance: " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\n";
   msg += "Trade by Equity: " + DoubleToString(InpTradeByEquityPct, 1) + "%\n";
   msg += "Currency Factor: " + DoubleToString(InpCurrencyFactor, 2);
   SendToMaster(msg);
}

void SendTradeConfirmation(PendingSignal &sig, double lot, double fill_price) {
   string msg = "✅ TRADE EXECUTED [HYDRA]\n";
   msg += "Signal: " + sig.signal_id + "\n";
   msg += "Account: " + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\n";
   msg += "Symbol: " + sig.symbol + "\n";
   msg += "Lot: " + DoubleToString(lot, 2) + "\n";
   msg += "Fill: " + DoubleToString(fill_price, _Digits);
   SendToMaster(msg);
}

void SendToMaster(string message) {
   // Send via WebRequest to Telegram Bot API
}

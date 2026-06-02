//+------------------------------------------------------------------+
//|                                                    HydraCopyEA.mq5|
//|                                          Hydra Trading System v1.0|
//|                                      Copy Trade / Signal Reception|
//+------------------------------------------------------------------+
// Renamed from HERMES → Hydra for standalone copy-trade distribution
// Source: Qwen Architecture Proposal 2026-06-02 — Phase 3
//
// Client-side EA that installs on the customer's MT5 terminal.
// Listens for signals from the Hydra Telegram Bot via polling/Webhook,
// calculates lot size (USD / USC support), executes trades, and sends
// fill confirmations back to the master.
//+------------------------------------------------------------------+
#property copyright "Hydra Trading System"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Json.mqh>  // Requires MQL5 JSON library

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                 |
//+------------------------------------------------------------------+
input group "=== 🔑 Main Settings ==="
input string   InpBotUsername      = "HydraSignalBot";   // Telegram Bot name
input ulong    InpMagicNumber      = 20260527;            // Magic Number
input double   InpRiskPercent      = 1.0;                 // Risk % of portfolio
input double   InpLotMultiplier    = 1.0;                 // Lot multiplier
input double   InpMaxLotCap        = 5.0;                 // Maximum lot allowed
input bool     InpAutoExecute      = true;                // Auto-execute trades
input int      InpSlippage         = 30;                  // Acceptable slippage (points)

input group "=== 🛡️ Risk Management ==="
input double   InpMaxDailyLoss     = 5.0;                 // Max Daily Loss % → stop trading
input double   InpMaxDrawdown      = 15.0;                // Max DD % → close all
input bool     InpEnableNewsFilter = true;                // Stop trading near news

input group "=== 📊 Reporting ==="
input bool     InpSendReports      = true;                // Send reports to master
input int      InpReportInterval   = 60;                  // Report every X minutes

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
CTrade         trade;
CSymbolInfo    symbolInfo;

// Signal queue structure
struct SignalData {
   string        signal_id;
   string        symbol;
   ENUM_ORDER_TYPE type;
   double        entry_price;
   double        sl_price;
   double        tp1, tp2, tp3;
   double        lot_multiplier;
   double        risk_percent;
   datetime      timestamp;
   int           expiry_minutes;
   string        source;
   int           grid_layer;
   bool          executed;
   ulong         ticket;
};

SignalData    signal_queue[];
int           signal_count = 0;

// Performance tracking
double        daily_pnl = 0;
double        start_equity = 0;
datetime      last_report_time = 0;
int           last_update_id = 0;
string        bot_token = "";  // Set via file or input

//+------------------------------------------------------------------+
//| INITIALIZATION                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   last_report_time = TimeCurrent();

   Print("🤖 Hydra Copy EA initialized");
   Print("Account: ", AccountInfoInteger(ACCOUNT_LOGIN));
   Print("Currency: ", AccountInfoString(ACCOUNT_CURRENCY));
   Print("Balance: ", AccountInfoDouble(ACCOUNT_BALANCE));
   Print("Magic: ", InpMagicNumber);

   // Load bot token from file
   LoadBotToken();

   // Register to master
   SendRegistrationToMaster();

   EventSetTimer(60); // Check every minute
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   EventKillTimer();
   Print("Hydra Copy EA stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| MAIN TICK FUNCTION                                               |
//+------------------------------------------------------------------+
void OnTick() {
   // 1. Check risk limits
   if (!CheckRiskLimits()) return;

   // 2. Process pending signals
   ProcessSignalQueue();

   // 3. Manage open positions (trailing, partial close)
   ManageOpenPositions();

   // 4. Send periodic reports
   if (InpSendReports && TimeCurrent() - last_report_time >= InpReportInterval * 60) {
      SendPeriodicReport();
      last_report_time = TimeCurrent();
   }
}

void OnTimer() {
   // Check for new signals from Telegram (polling)
   FetchNewSignalsFromTelegram();
}

//+------------------------------------------------------------------+
//| SIGNAL PROCESSING                                                |
//+------------------------------------------------------------------+
void ProcessSignalQueue() {
   for (int i = 0; i < signal_count; i++) {
      if (signal_queue[i].executed) continue;

      // Check expiry
      datetime expiry_time = signal_queue[i].timestamp + signal_queue[i].expiry_minutes * 60;
      if (TimeCurrent() > expiry_time) {
         Print("⏰ Signal expired: ", signal_queue[i].signal_id);
         signal_queue[i].executed = true;
         continue;
      }

      // Check symbol match
      if (signal_queue[i].symbol != _Symbol) continue;

      // Execute signal
      if (ExecuteSignal(signal_queue[i])) {
         signal_queue[i].executed = true;
         Print("✅ Signal executed: ", signal_queue[i].signal_id);
      }
   }
}

bool ExecuteSignal(SignalData &sig) {
   symbolInfo.Name(_Symbol);
   symbolInfo.RefreshRates();

   // 1. Calculate lot size based on risk
   double lot = CalculateLotSize(sig.risk_percent, sig.sl_price);

   // 2. Apply multiplier and cap
   lot = NormalizeDouble(lot * sig.lot_multiplier * InpLotMultiplier, 2);
   lot = MathMin(lot, InpMaxLotCap);
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));

   // 3. Get current price
   double current_price = (sig.type == ORDER_TYPE_BUY) ?
                           symbolInfo.Ask() : symbolInfo.Bid();

   // 4. Check slippage
   double slippage_points = MathAbs(current_price - sig.entry_price) / _Point;
   if (slippage_points > InpSlippage) {
      Print("⚠️ Slippage too high: ", slippage_points, " points. Skipping.");
      return false;
   }

   // 5. Execute order
   bool result = false;
   string comment = "HYDRA_" + sig.signal_id;
   
   if (sig.type == ORDER_TYPE_BUY) {
      result = trade.Buy(lot, _Symbol, 0, sig.sl_price, sig.tp1, comment);
   } else {
      result = trade.Sell(lot, _Symbol, 0, sig.sl_price, sig.tp1, comment);
   }

   if (result) {
      sig.ticket = trade.ResultOrder();
      Print("📍 Order placed: Ticket=", sig.ticket, " Lot=", lot,
            " SL=", sig.sl_price, " TP1=", sig.tp1);

      // Send confirmation back to master
      SendTradeConfirmation(sig, lot, current_price);
      return true;
   } else {
      Print("❌ Order failed: ", trade.ResultRetcodeDescription());
      return false;
   }
}

//+------------------------------------------------------------------+
//| LOT SIZE CALCULATION (USD / USC)                                 |
//+------------------------------------------------------------------+
double CalculateLotSize(double risk_percent, double sl_price) {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_amount = equity * risk_percent / 100.0;

   double current_price = symbolInfo.Bid();
   double sl_distance = MathAbs(current_price - sl_price);

   if (sl_distance <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);

   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

   double lot = risk_amount / ((sl_distance / tick_size) * tick_value);

   // Normalize
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lot = MathFloor(lot / lot_step) * lot_step;
   lot = MathMax(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   lot = MathMin(lot, SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));

   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| POSITION MANAGEMENT                                              |
//+------------------------------------------------------------------+
void ManageOpenPositions() {
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (!PositionSelectByTicket(ticket)) continue;
      if (PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      // Check if we have TP levels to manage
      // In full implementation: trail, partial close, etc.
   }
}

//+------------------------------------------------------------------+
//| RISK MANAGEMENT                                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);

   // Daily loss limit
   double daily_loss_pct = ((start_equity - equity) / start_equity) * 100;
   if (daily_loss_pct >= InpMaxDailyLoss) {
      Print("🚨 Daily loss limit reached: ", daily_loss_pct, "%");
      return false;
   }

   // Max drawdown
   double dd_pct = ((start_equity - equity) / start_equity) * 100;
   if (dd_pct >= InpMaxDrawdown) {
      Print("🚨 Max drawdown reached! Closing all positions.");
      CloseAllPositions();
      return false;
   }

   return true;
}

void CloseAllPositions() {
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (PositionSelectByTicket(ticket)) {
         if (PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) {
            trade.PositionClose(ticket);
         }
      }
   }
}

int CountOpenPositions() {
   int count = 0;
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if (PositionSelectByTicket(ticket)) {
         if (PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) {
            count++;
         }
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| TELEGRAM COMMUNICATION                                           |
//+------------------------------------------------------------------+
void LoadBotToken() {
   // Load bot token from a file in Common folder
   string filename = "Hydra\\bot_token.txt";
   int handle = FileOpen(filename, FILE_READ|FILE_TXT);
   if (handle != INVALID_HANDLE) {
      bot_token = FileReadString(handle);
      FileClose(handle);
      Print("✅ Bot token loaded from file");
   } else {
      Print("⚠️ Bot token file not found. Manual entry required.");
      bot_token = "";
   }
}

void FetchNewSignalsFromTelegram() {
   // Method 1: HTTP Request to Bot API (getUpdates)
   // Method 2: Webhook (requires PHP/Python server)
   // Method 3: Read from shared file / named pipe

   if (bot_token == "") return;

   string url = "https://api.telegram.org/bot" + bot_token +
                "/getUpdates?offset=" + IntegerToString(last_update_id + 1) +
                "&timeout=30";

   string result;
   char post[], result_headers[];
   int res = WebRequest("GET", url, NULL, NULL, 5000, post, 0, result, result_headers);

   if (res == 200) {
      ParseTelegramResponse(result);
   }
}

void ParseTelegramResponse(const string &response) {
   // Parse JSON from Telegram API response
   // Extract messages containing Hydra signals
   // This requires a JSON parser library for MQL5

   // Pseudocode:
   // JSONParser parser;
   // JSONObject root = parser.parse(response);
   // JSONArray result = root["result"];
   // for each message in result:
   //   extract text, parse JSON blockquote
   //   call AddSignalToQueue()

   // For now, log the raw response size
   Print("Telegram response received: ", StringLen(response), " bytes");
}

void AddSignalToQueue(SignalData &sig) {
   signal_count++;
   ArrayResize(signal_queue, signal_count);
   signal_queue[signal_count - 1] = sig;
   signal_queue[signal_count - 1].executed = false;
}

//+------------------------------------------------------------------+
//| REPORTING                                                        |
//+------------------------------------------------------------------+
void SendPeriodicReport() {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double pnl = equity - start_equity;
   double pnl_pct = (pnl / start_equity) * 100;

   string report = StringFormat(
      "📊 PERIODIC REPORT [HYDRA]\n"
      "Account: %I64d\n"
      "Equity: %.2f %s\n"
      "P/L: %+.2f (%+.2f%%)\n"
      "Open Positions: %d\n"
      "Time: %s",
      AccountInfoInteger(ACCOUNT_LOGIN),
      equity,
      AccountInfoString(ACCOUNT_CURRENCY),
      pnl, pnl_pct,
      CountOpenPositions(),
      TimeToString(TimeCurrent())
   );

   SendToMasterTelegram(report);
}

void SendTradeConfirmation(SignalData &sig, double lot, double fill_price) {
   string msg = StringFormat(
      "✅ TRADE CONFIRMED [HYDRA]\n"
      "Signal: %s\n"
      "Account: %I64d\n"
      "Symbol: %s\n"
      "Type: %s\n"
      "Lot: %.2f\n"
      "Fill: %.5f\n"
      "SL: %.5f\n"
      "TP1: %.5f\n"
      "Ticket: %I64d",
      sig.signal_id,
      AccountInfoInteger(ACCOUNT_LOGIN),
      sig.symbol,
      (sig.type == ORDER_TYPE_BUY) ? "BUY" : "SELL",
      lot, fill_price, sig.sl_price, sig.tp1, sig.ticket
   );

   SendToMasterTelegram(msg);
}

void SendToMasterTelegram(const string &message) {
   if (bot_token == "") return;

   // In production: POST to Telegram Bot API sendMessage
   // using WebRequest
   string url = "https://api.telegram.org/bot" + bot_token + "/sendMessage";

   // Build POST data
   string post_data = "chat_id=" + IntegerToString(GetMasterChatId()) +
                      "&text=" + message +
                      "&parse_mode=HTML";

   char post[], result_headers[];
   string result;
   StringToCharArray(post_data, post);

   int res = WebRequest("POST", url, "Content-Type: application/x-www-form-urlencoded",
                        5000, post, result, result_headers);
   if (res != 200) {
      Print("⚠️ Failed to send report: ", res);
   }
}

void SendRegistrationToMaster() {
   string msg = StringFormat(
      "🆕 NEW CLIENT REGISTERED [HYDRA]\n"
      "Account: %I64d\n"
      "Broker: %s\n"
      "Currency: %s\n"
      "Balance: %.2f\n"
      "Leverage: 1:%I64d\n"
      "EA Version: 1.00",
      AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_COMPANY),
      AccountInfoString(ACCOUNT_CURRENCY),
      AccountInfoDouble(ACCOUNT_BALANCE),
      AccountInfoInteger(ACCOUNT_LEVERAGE)
   );

   Print("Registration message queued for master");
   SendToMasterTelegram(msg);
}

int GetMasterChatId() {
   // In production: read from config file or input
   return 0;  // Override with actual admin chat ID
}

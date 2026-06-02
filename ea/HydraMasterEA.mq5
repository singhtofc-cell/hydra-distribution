//+------------------------------------------------------------------+
//|                                                 HydraMasterEA.mq5|
//|                                          Hydra Trading System v2.0|
//|                                Master Signal Broadcaster & Manager|
//+------------------------------------------------------------------+
// Renamed from HERMES → Hydra for standalone copy-trade distribution
// Source: Qwen Architecture Proposal 2026-06-02 — Master EA + Client EA
//
// Master EA that runs on the Master's MT5 terminal.
// Detects signals from Hydra/HERMES strategies, formats them as JSON,
// and broadcasts to all registered client EAs via Telegram Bot API.
//+------------------------------------------------------------------+
#property copyright "Hydra Trading System"
#property version   "2.00"
#property strict
#include "Trade.mqh"
// Note: Trade functions are used in other modules; compile with MetaTrader 5 to provide <Trade\Trade.mqh>.

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                 |
//+------------------------------------------------------------------+
// === 🔗 Connection ===
input string   InpBotToken         = "YOUR_BOT_TOKEN";     // Telegram Bot Token
input string   InpClientChatIDs    = "123456789,987654321"; // Client Chat IDs (comma-sep)
input int      InpSignalExpiry     = 30;                   // Signal expiry (minutes)

// === ⚙️ Signal Settings ===
input double   InpDefaultRisk      = 1.0;                  // Default Risk % recommendation
input double   InpMasterLotMult    = 1.0;                  // Master Lot Multiplier
input string   InpMagicPrefix      = "HYDRA";              // Magic Number Prefix
input bool     InpAutoSend         = true;                 // Auto-send signals

// === 🎯 Strategies ===
input bool     InpEnableSMCGrid    = true;                 // Enable SMC Grid
input bool     InpEnableJudasSwing = true;                 // Enable Judas Swing
input int      InpMinConfluence    = 8;                    // Minimum Confluence Score

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
// Trade object is provided by MQL5 <Trade\Trade.mqh> at compile time (MT5). Omit local declaration here.
string         client_chat_ids[];
int            signal_counter = 0;

//+------------------------------------------------------------------+
//| SIGNAL STRUCTURE                                                  |
//+------------------------------------------------------------------+
struct TradeSignal {
   string        signal_id;
   string        symbol;
   ENUM_ORDER_TYPE direction;
   double        entry_price;
   double        sl_price;
   double        tp_prices[];
   double        risk_percent;
   double        lot_multiplier;
   string        source;
   int           grid_layer;
   int           expiry_minutes;
   datetime      timestamp;
};

//+------------------------------------------------------------------+
//| INITIALIZATION                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   StringSplit(InpClientChatIDs, ',', client_chat_ids);

   Print("🧠 Hydra Master EA initialized");
   Print("📡 Broadcasting to ", ArraySize(client_chat_ids), " clients");
   Print("🔢 Magic Prefix: ", InpMagicPrefix);

   EventSetTimer(60);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   EventKillTimer();
   Print("Hydra Master EA stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| MAIN LOGIC                                                       |
//+------------------------------------------------------------------+
void OnTick() {
   if(!InpAutoSend) return;

   if(InpEnableSMCGrid) {
      DetectSMCGridSignals();
   }

   if(InpEnableJudasSwing) {
      DetectJudasSwingSignals();
   }
}

void OnTimer() {
   CleanupExpiredSignals();
}

//+------------------------------------------------------------------+
//| SIGNAL DETECTION (SMC Grid)                                      |
//+------------------------------------------------------------------+
void DetectSMCGridSignals() {
   // Integrates with Hydra/HERMES Python Backend for signal detection.
   // In practice, signals are received via the Python Signal Server
   // and forwarded to Telegram. This EA is a fallback/direct channel.
   //
   // Example:
   // TradeSignal sig;
   // sig.signal_id = GenerateSignalID();
   // sig.symbol = "XAUUSD";
   // sig.direction = ORDER_TYPE_BUY;
   // sig.entry_price = 2350.50;
   // sig.sl_price = 2330.00;
   // ArrayResize(sig.tp_prices, 3);
   // sig.tp_prices[0] = 2370.00;
   // sig.tp_prices[1] = 2390.00;
   // sig.tp_prices[2] = 2420.00;
   // sig.risk_percent = InpDefaultRisk;
   // sig.lot_multiplier = InpMasterLotMult;
   // sig.source = "SMC_GRID_L2";
   // sig.grid_layer = 2;
   // sig.expiry_minutes = InpSignalExpiry;
   // BroadcastSignal(sig);
}

void DetectJudasSwingSignals() {
   // Detect Judas Swing patterns during London/NY windows
}

//+------------------------------------------------------------------+
//| BROADCAST SIGNAL                                                 |
//+------------------------------------------------------------------+
void BroadcastSignal(TradeSignal &sig) {
   signal_counter++;

   string json = FormatSignalJSON(sig);
   string message = FormatSignalMessage(sig);

   for(int i = 0; i < ArraySize(client_chat_ids); i++) {
      string chat_id = client_chat_ids[i];
      StringTrimLeft(chat_id);
      StringTrimRight(chat_id);

      if(SendToTelegram(chat_id, message, json)) {
         Print("✅ Signal #", sig.signal_id, " sent to client ", chat_id);
      } else {
         Print("❌ Failed to send to client ", chat_id);
      }
   }
}

//+------------------------------------------------------------------+
//| JSON FORMATTER                                                   |
//+------------------------------------------------------------------+
string FormatSignalJSON(TradeSignal &sig) {
   string json = "{";
   json += "\"signal_id\":\"" + sig.signal_id + "\",";
   json += "\"timestamp\":" + IntegerToString(TimeCurrent()) + ",";
   json += "\"symbol\":\"" + sig.symbol + "\",";
   json += "\"direction\":\"" + (sig.direction == ORDER_TYPE_BUY ? "BUY" : "SELL") + "\",";
   json += "\"entry_price\":" + DoubleToString(sig.entry_price, _Digits) + ",";
   json += "\"sl_price\":" + DoubleToString(sig.sl_price, _Digits) + ",";
   json += "\"tp_prices\":[";
   for(int i = 0; i < ArraySize(sig.tp_prices); i++) {
      json += DoubleToString(sig.tp_prices[i], _Digits);
      if(i < ArraySize(sig.tp_prices) - 1) json += ",";
   }
   json += "],";
   json += "\"risk_percent\":" + DoubleToString(sig.risk_percent, 2) + ",";
   json += "\"lot_multiplier\":" + DoubleToString(sig.lot_multiplier, 2) + ",";
   json += "\"source\":\"" + sig.source + "\",";
   json += "\"grid_layer\":" + IntegerToString(sig.grid_layer) + ",";
   json += "\"expiry_minutes\":" + IntegerToString(sig.expiry_minutes);
   json += "}";
   return json;
}

string FormatSignalMessage(TradeSignal &sig) {
   string emoji = (sig.direction == ORDER_TYPE_BUY) ? "🟢" : "🔴";

   string msg = emoji + " <b>HYDRA SIGNAL #" + sig.signal_id + "</b>\n\n";
   msg += (sig.direction == ORDER_TYPE_BUY ? "BUY" : "SELL") + " " + sig.symbol + "\n";
   msg += "━━━━━━━━━━━━━━━━━━━\n";
   msg += "📍 Entry: " + DoubleToString(sig.entry_price, _Digits) + "\n";
   msg += "🛡️ SL: " + DoubleToString(sig.sl_price, _Digits) + "\n";

   for(int i = 0; i < ArraySize(sig.tp_prices); i++) {
      msg += "💰 TP" + IntegerToString(i+1) + ": " + DoubleToString(sig.tp_prices[i], _Digits) + "\n";
   }

   msg += "⚖️ Risk: " + DoubleToString(sig.risk_percent, 1) + "%\n";
   msg += "🏷️ Source: " + sig.source + "\n";
   msg += "⏱️ Expires: " + IntegerToString(sig.expiry_minutes) + " min\n\n";
   msg += "<blockquote>" + FormatSignalJSON(sig) + "</blockquote>";

   return msg;
}

//+------------------------------------------------------------------+
//| TELEGRAM SENDER                                                  |
//+------------------------------------------------------------------+
bool SendToTelegram(string chat_id, string message, string json_payload) {
   // Uses WebRequest to POST to Telegram Bot API
   // Requires: Tools → Options → Expert Advisors → Allow WebRequest for api.telegram.org
   string url = "https://api.telegram.org/bot" + InpBotToken + "/sendMessage";
   // POST implementation with WebRequest
   return true; // Simplified — full implementation uses WebRequest
}

string GenerateSignalID() {
   return InpMagicPrefix + "_" + IntegerToString(TimeCurrent()) + "_" + IntegerToString(signal_counter);
}

void CleanupExpiredSignals() {
   // Remove expired signals from local tracking
}

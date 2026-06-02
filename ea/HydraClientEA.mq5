//+------------------------------------------------------------------+
//|                                               HydraClientEA.mq5  |
//|                                          Hydra Trading System v3.10|
//|                         Client EA with Manual Trade Detection + Telegram |
//+------------------------------------------------------------------+
// Renamed from HERMES → Hydra for standalone copy-trade distribution
// Source: Qwen Architecture Proposal 2026-06-02 — Client EA + Telegram
//
// Client-side EA that installs on the customer's OWN PC (alongside
// Telegram Desktop). Client logs into MT5 themselves, enables Algo
// Trading, and configures risk % directly via Telegram chatbot.
// No VPS needed — runs on the same machine as Telegram.
//+------------------------------------------------------------------+
#property copyright "Hydra Trading System"
#property version   "3.10"
#property description "ระบบ Copy Trade อัตโนมัติ พร้อมตรวจจับ Manual Trade และตั้งค่าผ่าน Telegram"
#property strict
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\AccountInfo.mqh>

//+------------------------------------------------------------------+
//| INPUT PARAMETERS — Client sets these via Telegram                |
//+------------------------------------------------------------------+
input group "=== 🔑 Telegram Settings ==="
input string   InpBotToken         = "";           // Bot Token from Master
input long     InpMasterChatID     = 0;            // Master Chat ID
input string   InpTelegramUsername = "";           // Client's Telegram username (no @)

input group "=== 💰 Risk Management ==="
input double   InpRiskPerTrade     = 1.0;          // Risk % per trade (1.0 = 1%)
input double   InpMaxDailyLoss     = 5.0;          // Max Daily Loss % (stops trading)
input double   InpMaxDrawdown      = 15.0;         // Max Drawdown % (closes all)
input double   InpMaxLotCap        = 10.0;         // Max lot allowed

input group "=== 📊 Account Type ==="
input bool     InpIsCentAccount    = false;        // true for Cent (USC)
input double   InpCurrencyFactor   = 1.0;          // 1.0 (USD) or 100.0 (USC)

input group "=== ⚙️ EA Settings ==="
input ulong    InpMagicNumber      = 20260527;     // Magic Number
input int      InpSlippage         = 30;           // Slippage (points)
input bool     InpAutoTrade        = true;         // Auto-execute trades
input int      InpPollInterval     = 5;            // Poll interval (seconds)

input group "=== 🛡️ Safety ==="
input bool     InpRequireConfirmation = true;      // Require confirmation before trade
input double   InpMinMarginLevel   = 200.0;        // Min Margin Level (%)
input bool     InpAllowManualTrades = false;       // อนุญาตให้เปิดเองโดยไม่แจ้งเตือน

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
CTrade         trade;
CSymbolInfo    symbolInfo;
CAccountInfo   accountInfo;

int            last_update_id = 0;
datetime       last_poll_time = 0;
bool           is_registered = false;
string         my_chat_id = "";

double         start_equity = 0;
double         daily_start_equity = 0;
datetime       daily_reset_time = 0;
int            trades_today = 0;

struct TradeSignal {
   string   signal_id;
   string   symbol;
   int      direction;       // 1 = BUY, -1 = SELL
   double   entry_price;
   double   sl_price;
   double   tp1, tp2, tp3;
   double   risk_percent;
   datetime timestamp;
   int      expiry_minutes;
   bool     executed;
};

TradeSignal    signal_queue[];
int            signal_count = 0;

double         current_risk_percent = 1.0;
bool           trading_enabled = true;

// 🚨 Manual Trade Detection
ulong          warned_manual_tickets[];
int            warned_ticket_count = 0;

//+------------------------------------------------------------------+
//| INITIALIZATION                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   if(InpBotToken == "") { Alert("❌ กรุณาใส่ Bot Token"); return(INIT_FAILED); }
   if(InpMasterChatID == 0) { Alert("❌ กรุณาใส่ Master Chat ID"); return(INIT_FAILED); }

   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   start_equity = accountInfo.Equity();
   daily_start_equity = start_equity;
   daily_reset_time = TimeCurrent();
   current_risk_percent = InpRiskPerTrade;

   Print("🤖 Hydra Client EA v3.10 initialized");
   Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
   Print("💰 Account: ", accountInfo.Login());
   Print("💵 Balance: ", accountInfo.Balance(), " ", accountInfo.Currency());
   Print("📊 Equity: ", accountInfo.Equity());
   Print("⚖️ Risk per Trade: ", current_risk_percent, "%");
   Print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

   SendRegistrationToMaster();
   EventSetTimer(InpPollInterval);

   SendToClient("🤖 <b>Hydra Client EA เริ่มต้นทำงานแล้ว!</b>\n\n" +
                "💰 บัญชี: " + IntegerToString(accountInfo.Login()) + "\n" +
                "💵 ยอดเงิน: " + DoubleToString(accountInfo.Balance(), 2) + " " + accountInfo.Currency() + "\n" +
                "⚖️ ความเสี่ยง: " + DoubleToString(current_risk_percent, 1) + "%\n\n" +
                "ใช้ /start เพื่อลงทะเบียนกับ Bot");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   EventKillTimer();
   SendToClient("⚠️ Hydra Client EA หยุดทำงาน\nเหตุผล: " + IntegerToString(reason));
}

//+------------------------------------------------------------------+
//| MAIN TICK                                                        |
//+------------------------------------------------------------------+
void OnTick() {
   // 1. 🚨 ตรวจจับการเทรดด้วยตนเอง (Manual Trade) เป็นอันดับแรก
   if(!InpAllowManualTrades) { CheckAndWarnManualTrades(); }

   CheckDailyReset();
   if(!CheckRiskLimits()) return;
   if(InpAutoTrade && trading_enabled) ProcessSignalQueue();
   ManageOpenPositions();
}

void OnTimer() {
   PollTelegramMessages();
}

//+------------------------------------------------------------------+
//| TELEGRAM — Poll & Parse                                          |
//+------------------------------------------------------------------+
void PollTelegramMessages() {
   if(TimeCurrent() - last_poll_time < InpPollInterval) return;
   last_poll_time = TimeCurrent();

   string url = "https://api.telegram.org/bot" + InpBotToken +
                "/getUpdates?offset=" + IntegerToString(last_update_id + 1) +
                "&timeout=1";

   char post[], result[];
   string result_headers;
   int res = WebRequest("GET", url, NULL, NULL, 5000, post, 0, result, result_headers);

   if(res == 200) {
      string response = CharArrayToString(result);
      ParseTelegramResponse(response);
   }
}

void ParseTelegramResponse(const string &response) {
   int pos = 0;
   while((pos = StringFind(response, "\"update_id\":", pos)) >= 0) {
      pos += 12;
      int end_pos = StringFind(response, ",", pos);
      string update_id_str = StringSubstr(response, pos, end_pos - pos);
      int update_id = (int)StringToInteger(update_id_str);
      if(update_id > last_update_id) {
         last_update_id = update_id;
         int chat_pos = StringFind(response, "\"chat\":{\"id\":", pos);
         if(chat_pos >= 0) {
            chat_pos += 13;
            int chat_end = StringFind(response, "}", chat_pos);
            string chat_id_str = StringSubstr(response, chat_pos, chat_end - chat_pos);
            long chat_id = StringToInteger(chat_id_str);
            int text_pos = StringFind(response, "\"text\":\"", chat_pos);
            if(text_pos >= 0) {
               text_pos += 8;
               int text_end = StringFind(response, "\"", text_pos);
               string text = StringSubstr(response, text_pos, text_end - text_pos);
               ProcessTelegramCommand(chat_id, text);
            }
         }
      }
   }
}

void ProcessTelegramCommand(long chat_id, string text) {
   if(chat_id != StringToInteger(my_chat_id) && my_chat_id != "") return;

   StringToLower(text);
   StringTrimLeft(text);
   StringTrimRight(text);

   if(StringFind(text, "/start") == 0) {
      my_chat_id = IntegerToString(chat_id);
      SendToClient("✅ <b>ลงทะเบียนสำเร็จ!</b>\n\n" +
                   "💰 บัญชี: " + IntegerToString(accountInfo.Login()) + "\n" +
                   "⚖️ ความเสี่ยง: " + DoubleToString(current_risk_percent, 1) + "%\n\n" +
                   "ใช้ /help เพื่อดูคำสั่งทั้งหมด");
      SendToMaster("✅ ลูกค้าเชื่อมต่อแล้ว\nบัญชี: " + IntegerToString(accountInfo.Login()) +
                   "\nChat ID: " + my_chat_id);
   }
   else if(StringFind(text, "/status") == 0) {
      string s = "📊 <b>สถานะปัจจุบัน</b>\n\n";
      s += "💰 Equity: " + DoubleToString(accountInfo.Equity(), 2) + "\n";
      s += "📈 P/L วันนี้: " + DoubleToString(accountInfo.Equity() - daily_start_equity, 2) + "\n";
      s += "⚖️ ความเสี่ยง: " + DoubleToString(current_risk_percent, 1) + "%\n";
      s += "🎯 เทรดวันนี้: " + IntegerToString(trades_today) + "\n";
      s += "📊 Position เปิด: " + IntegerToString(CountOpenPositions()) + "\n";
      s += "🔄 สถานะ: " + (trading_enabled ? "✅ กำลังเทรด" : "⏸️ หยุดชั่วคราว");
      SendToClient(s);
   }
   else if(StringFind(text, "/risk") == 0) {
      string val = StringSubstr(text, 6);
      StringTrimLeft(val);
      double new_risk = StringToDouble(val);
      if(new_risk >= 0.1 && new_risk <= 10.0) {
         current_risk_percent = new_risk;
         SendToClient("✅ ตั้งค่าความเสี่ยงใหม่: " + DoubleToString(current_risk_percent, 1) + "%");
         SendToMaster("🔄 ลูกค้าเปลี่ยนความเสี่ยง\nบัญชี: " + IntegerToString(accountInfo.Login()) +
                      "\nค่าใหม่: " + DoubleToString(current_risk_percent, 1) + "%");
      } else {
         SendToClient("❌ ค่าไม่ถูกต้อง (0.1-10.0)\nตัวอย่าง: /risk 2.0");
      }
   }
   else if(StringFind(text, "/pause") == 0) {
      trading_enabled = false;
      SendToClient("⏸️ หยุดรับการเทรด\nใช้ /resume เพื่อเปิดอีกครั้ง");
   }
   else if(StringFind(text, "/resume") == 0) {
      trading_enabled = true;
      SendToClient("▶️ เปิดรับการเทรดอีกครั้ง");
   }
   else if(StringFind(text, "/report") == 0) { SendDailyReport(); }
   else if(StringFind(text, "/help") == 0) {
      string h = "📖 <b>คำสั่งที่ใช้ได้</b>\n\n";
      h += "/status — ดูสถานะ\n";
      h += "/risk [ตัวเลข] — ตั้งค่าความเสี่ยง\n   เช่น /risk 2.0\n";
      h += "/pause — หยุดเทรด\n";
      h += "/resume — เปิดเทรด\n";
      h += "/report — รายงานวันนี้\n";
      h += "/help — เมนูนี้\n\n";
      h += "⚖️ ความเสี่ยง: " + DoubleToString(current_risk_percent, 1) + "%";
      SendToClient(h);
   }
   else if(StringFind(text, "hydra_signal_") == 0) {
      ParseTradeSignal(text);
   }
}

//+------------------------------------------------------------------+
//| TELEGRAM — Send                                                  |
//+------------------------------------------------------------------+
void SendToClient(string msg) {
   if(my_chat_id == "") return;
   string url = "https://api.telegram.org/bot" + InpBotToken + "/sendMessage";
   string data = "chat_id=" + my_chat_id + "&text=" + UrlEncode(msg) +
                 "&parse_mode=HTML&disable_web_page_preview=true";
   char post[], result[];
   string hdrs;
   StringToCharArray(data, post);
   WebRequest("POST", url, NULL, NULL, 5000, post, 0, result, hdrs);
}

void SendToMaster(string msg) {
   string url = "https://api.telegram.org/bot" + InpBotToken + "/sendMessage";
   string data = "chat_id=" + IntegerToString(InpMasterChatID) + "&text=" + UrlEncode(msg);
   char post[], result[];
   string hdrs;
   StringToCharArray(data, post);
   WebRequest("POST", url, NULL, NULL, 5000, post, 0, result, hdrs);
}

string UrlEncode(string str) {
   StringReplace(str, " ", "%20");
   StringReplace(str, "\n", "%0A");
   StringReplace(str, "&", "%26");
   StringReplace(str, "=", "%3D");
   StringReplace(str, "?", "%3F");
   StringReplace(str, "#", "%23");
   return str;
}

//+------------------------------------------------------------------+
//| REGISTRATION                                                     |
//+------------------------------------------------------------------+
void SendRegistrationToMaster() {
   string msg = "🆕 <b>ลูกค้าใหม่ลงทะเบียน</b>\n\n";
   msg += "💰 บัญชี: " + IntegerToString(accountInfo.Login()) + "\n";
   msg += "💵 Balance: " + DoubleToString(accountInfo.Balance(), 2) + " " + accountInfo.Currency() + "\n";
   msg += "📊 Equity: " + DoubleToString(accountInfo.Equity(), 2) + "\n";
   msg += "⚖️ Leverage: 1:" + IntegerToString(accountInfo.Leverage()) + "\n";
   msg += "⚙️ Risk: " + DoubleToString(current_risk_percent, 1) + "%\n";
   msg += "🔢 Factor: " + DoubleToString(InpCurrencyFactor, 1) + "\n";
   msg += "📱 Acc Type: " + (InpIsCentAccount ? "Cent (USC)" : "Standard (USD)");
   SendToMaster(msg);
}

//+------------------------------------------------------------------+
//| SIGNAL PROCESSING                                                |
//+------------------------------------------------------------------+
void ParseTradeSignal(string signal_text) {
   string parts[];
   int count = StringSplit(signal_text, '_', parts);
   if(count < 9) { Print("❌ Invalid signal format"); return; }

   TradeSignal sig;
   sig.signal_id = parts[2];
   sig.symbol = parts[3];
   sig.direction = (StringFind(parts[2], "BUY") >= 0) ? 1 : -1;
   sig.entry_price = StringToDouble(parts[4]);
   sig.sl_price = StringToDouble(parts[5]);
   sig.tp1 = StringToDouble(parts[6]);
   sig.tp2 = StringToDouble(parts[7]);
   sig.tp3 = StringToDouble(parts[8]);
   sig.risk_percent = (count > 9) ? StringToDouble(parts[9]) : current_risk_percent;
   sig.expiry_minutes = (count > 10) ? (int)StringToInteger(parts[10]) : 30;
   sig.timestamp = TimeCurrent();
   sig.executed = false;

   signal_count++;
   ArrayResize(signal_queue, signal_count);
   signal_queue[signal_count - 1] = sig;

   string dir = (sig.direction == 1) ? "BUY" : "SELL";
   Print("📩 Signal: ", sig.signal_id, " ", sig.symbol, " ", dir);

   string emoji = (sig.direction == 1) ? "🟢" : "🔴";
   SendToClient(emoji + " <b>สัญญาณเทรดใหม่</b>\n\n" +
                "📊 " + sig.symbol + "\n" +
                "🎯 " + dir + "\n" +
                "📍 " + DoubleToString(sig.entry_price, 2) + "\n" +
                "🛡️ SL: " + DoubleToString(sig.sl_price, 2) + "\n" +
                "💰 TP1: " + DoubleToString(sig.tp1, 2) + "\n" +
                "⚖️ Risk: " + DoubleToString(sig.risk_percent, 1) + "%\n" +
                "⏱️ หมดอายุ " + IntegerToString(sig.expiry_minutes) + " นาที\n\nกำลังเปิดออเดอร์...");
}

void ProcessSignalQueue() {
   for(int i = 0; i < signal_count; i++) {
      if(signal_queue[i].executed) continue;
      datetime expiry = signal_queue[i].timestamp + signal_queue[i].expiry_minutes * 60;
      if(TimeCurrent() > expiry) {
         signal_queue[i].executed = true;
         SendToClient("⏰ สัญญาณหมดอายุ: " + signal_queue[i].signal_id);
         continue;
      }
      if(ExecuteTrade(signal_queue[i])) {
         signal_queue[i].executed = true;
         trades_today++;
      }
   }
}

bool ExecuteTrade(TradeSignal &sig) {
   if(sig.symbol != _Symbol) return false;

   symbolInfo.Name(_Symbol);
   symbolInfo.RefreshRates();

   double lot = CalculateLotSize(sig.risk_percent, sig.sl_price, sig.entry_price);
   if(lot <= 0) { SendToClient("❌ ไม่สามารถคำนวณ Lot"); return false; }

   double spread = symbolInfo.Spread() * _Point;
   if(spread > symbolInfo.Ask() * 0.002) { Print("⚠️ Spread too high"); return false; }

   double margin_level = accountInfo.MarginLevel();
   if(margin_level > 0 && margin_level < InpMinMarginLevel) {
      SendToClient("⚠️ Margin Level ต่ำ: " + DoubleToString(margin_level, 0) + "%");
      return false;
   }

   bool result = false;
   double current_price = 0;
   if(sig.direction == 1) {
      current_price = symbolInfo.Ask();
      result = trade.Buy(lot, _Symbol, current_price, sig.sl_price, sig.tp1,
                         "HYDRA_" + sig.signal_id);
   } else {
      current_price = symbolInfo.Bid();
      result = trade.Sell(lot, _Symbol, current_price, sig.sl_price, sig.tp1,
                          "HYDRA_" + sig.signal_id);
   }

   if(result) {
      ulong ticket = trade.ResultOrder();
      Print("✅ Order: Ticket=", ticket, " Lot=", lot);
      string emoji = (sig.direction == 1) ? "🟢" : "🔴";
      SendToClient(emoji + " <b>เปิดออเดอร์แล้ว</b>\n\n" +
                   "🎫 Ticket: " + IntegerToString(ticket) + "\n" +
                   "📊 " + _Symbol + "\n" +
                   "🎯 " + (sig.direction == 1 ? "BUY" : "SELL") + "\n" +
                   "📦 Lot: " + DoubleToString(lot, 2) + "\n" +
                   "📍 " + DoubleToString(current_price, _Digits) + "\n" +
                   "🛡️ SL: " + DoubleToString(sig.sl_price, _Digits));
      SendToMaster("✅ ลูกค้าเปิดออเดอร์\nบัญชี: " + IntegerToString(accountInfo.Login()) +
                   "\nTicket: " + IntegerToString(ticket) +
                   "\nLot: " + DoubleToString(lot, 2) +
                   "\nSymbol: " + _Symbol);
      return true;
   }
   SendToClient("❌ เปิดออเดอร์ล้มเหลว\n" + trade.ResultRetcodeDescription());
   return false;
}

//+------------------------------------------------------------------+
//| LOT SIZE CALCULATION                                             |
//+------------------------------------------------------------------+
double CalculateLotSize(double risk_percent, double sl_price, double entry_price) {
   double equity = accountInfo.Equity();
   double risk_amount = equity * (risk_percent / 100.0);
   double sl_distance = MathAbs(entry_price - sl_price);
   if(sl_distance <= 0) return 0;

   double tick_value = symbolInfo.TickValue();
   double tick_size = symbolInfo.TickSize();
   if(tick_value <= 0 || tick_size <= 0) return 0;

   double lot = risk_amount / ((sl_distance / tick_size) * tick_value);
   lot *= InpCurrencyFactor;

   double lot_step = symbolInfo.LotsStep();
   lot = MathFloor(lot / lot_step) * lot_step;
   lot = MathMax(lot, symbolInfo.LotsMin());
   lot = MathMin(lot, InpMaxLotCap);
   lot = MathMin(lot, symbolInfo.LotsMax());

   double required_margin = (lot * symbolInfo.ContractSize() * symbolInfo.Ask() *
                             symbolInfo.MarginInitial()) / accountInfo.Leverage();
   double free_margin = accountInfo.FreeMargin();
   if(required_margin > free_margin * 0.8) {
      lot = lot * (free_margin * 0.8 / required_margin);
      lot = MathFloor(lot / lot_step) * lot_step;
      lot = MathMax(lot, symbolInfo.LotsMin());
   }
   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| RISK MANAGEMENT                                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   double equity = accountInfo.Equity();
   double daily_loss = ((daily_start_equity - equity) / daily_start_equity) * 100;
   if(daily_loss >= InpMaxDailyLoss) {
      if(trading_enabled) {
         trading_enabled = false;
         SendToClient("🚨 <b>หยุดเทรด</b> ขาดทุน " + DoubleToString(daily_loss, 1) +
                      "% แล้ว\nใช้ /resume เพื่อเปิดอีกครั้ง");
      }
      return false;
   }
   double dd = ((start_equity - equity) / start_equity) * 100;
   if(dd >= InpMaxDrawdown) {
      CloseAllPositions();
      SendToClient("🚨 <b>ปิดออเดอร์ทั้งหมด</b> Drawdown " + DoubleToString(dd, 1) + "%");
      return false;
   }
   return true;
}

void CheckDailyReset() {
   MqlDateTime dt, last_dt;
   TimeCurrent(dt);
   TimeToStruct(daily_reset_time, last_dt);
   if(dt.day != last_dt.day) {
      daily_start_equity = accountInfo.Equity();
      daily_reset_time = TimeCurrent();
      trades_today = 0;
      trading_enabled = true;
      SendToClient("🔄 <b>วันใหม่</b>\n💰 Equity: " + DoubleToString(daily_start_equity, 2));
   }
}

void CloseAllPositions() {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) trade.PositionClose(ticket);
   }
}

//+------------------------------------------------------------------+
//| HELPERS                                                          |
//+------------------------------------------------------------------+
int CountOpenPositions() {
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber) count++;
   return count;
}

void ManageOpenPositions() {
   // Trailing stop, partial close — extend per strategy
}

//+------------------------------------------------------------------+
//| 🚨 MANUAL TRADE DETECTION & WARNING SYSTEM                       |
//| Source: Qwen Article 2026-06-02                                   |
//+------------------------------------------------------------------+
void CheckAndWarnManualTrades() {
   // วนตรวจสอบทุก Position ในพอร์ต
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      long   pos_magic  = PositionGetInteger(POSITION_MAGIC);
      string pos_symbol = PositionGetString(POSITION_SYMBOL);
      string pos_comment= PositionGetString(POSITION_COMMENT);
      long   pos_type   = PositionGetInteger(POSITION_TYPE);
      double pos_lot    = PositionGetDouble(POSITION_VOLUME);

      // เงื่อนไขการตรวจจับออเดอร์นอกระบบ (Manual หรือ EA อื่น):
      // 1. Magic Number ไม่ตรงกับ Hydra
      // 2. หรือ Comment ไม่ขึ้นต้นด้วย "HYDRA_"
      bool is_manual_trade = false;

      if(pos_magic != InpMagicNumber) {
         is_manual_trade = true;
      } else if(StringFind(pos_comment, "HYDRA_") != 0) {
         is_manual_trade = true;
      }

      // ถ้าเจอออเดอร์นอกระบบ และยังไม่เคยแจ้งเตือน Ticket นี้
      if(is_manual_trade) {
         if(!IsTicketAlreadyWarned(ticket)) {
            SendManualTradeTelegramWarning(ticket, pos_symbol, pos_type, pos_lot, pos_comment);
            AddWarnedTicket(ticket);
         }
      }
   }
}

// ตรวจสอบว่าแจ้งเตือน Ticket นี้ไปหรือยัง
bool IsTicketAlreadyWarned(ulong ticket) {
   for(int i = 0; i < warned_ticket_count; i++) {
      if(warned_manual_tickets[i] == ticket) return true;
   }
   return false;
}

// บันทึก Ticket ที่แจ้งเตือนแล้ว
void AddWarnedTicket(ulong ticket) {
   warned_ticket_count++;
   ArrayResize(warned_manual_tickets, warned_ticket_count);
   warned_manual_tickets[warned_ticket_count - 1] = ticket;
   Print("⚠️ Manual trade detected and warned: Ticket #", ticket);
}

// ฟังก์ชันส่งข้อความเตือนไป Telegram (สวยงามและเด่นชัด)
void SendManualTradeTelegramWarning(ulong ticket, string symbol, long type, double lot, string comment) {
   string type_str = (type == POSITION_TYPE_BUY) ? "🟢 BUY" : "🔴 SELL";

   // ข้อความเตือนพิเศษตามที่คุณกำหนด
   string warning_msg = "🚨 <b>คำเตือน: ตรวจจับการเทรดด้วยตนเอง (Manual Trade)</b> 🚨\n\n";
   warning_msg += "⚠️ <i>การเทรดแบบนอกเหนือความเสี่ยงที่ออกแบบมาจากระบบ ";
   warning_msg += "อาจส่งผลให้การเทรดด้วยระบบคำนวณผิดพลาด นำมาสู่การสูญเสีย ";
   warning_msg += "ระบบไม่สามารถปรับตัวเข้ากับการตัดสินใจของคุณเองได้</i>\n\n";

   warning_msg += "━━━━━━━━━━━━━━━━━━━━\n";
   warning_msg += "📊 <b>รายละเอียดออเดอร์ที่ตรวจจับได้:</b>\n";
   warning_msg += "🎫 Ticket: <code>" + IntegerToString(ticket) + "</code>\n";
   warning_msg += "📈 Symbol: " + symbol + "\n";
   warning_msg += "🎯 Direction: " + type_str + "\n";
   warning_msg += "📦 Lot Size: " + DoubleToString(lot, 2) + "\n";
   warning_msg += "📝 Comment: " + (comment == "" ? "<i>ไม่มี (เปิดเอง)</i>" : comment) + "\n";
   warning_msg += "━━━━━━━━━━━━━━━━━━━━\n\n";

   warning_msg += "💡 <b>คำแนะนำ:</b>\n";
   warning_msg += "1. กรุณาปิดออเดอร์นี้หากต้องการให้ระบบ Hydra คำนวณความเสี่ยงให้\n";
   warning_msg += "2. รอรับสัญญาณและให้ EA เปิดออเดอร์อัตโนมัติเท่านั้น\n";
   warning_msg += "3. ใช้คำสั่ง /pause หากต้องการหยุดระบบชั่วคราว\n\n";
   warning_msg += "🛡️ <i>Hydra Risk Management System</i>";

   // ส่งไปยัง Telegram ของลูกค้า
   SendToClient(warning_msg);

   // ส่งรายงานไปยัง Master (คุณ) ด้วย
   string master_alert = "🚨 ลูกค้าเปิดออเดอร์เอง (Manual Trade)\n";
   master_alert += "บัญชี: " + IntegerToString(accountInfo.Login()) + "\n";
   master_alert += "Ticket: " + IntegerToString(ticket) + "\n";
   master_alert += "Symbol: " + symbol + " | " + type_str + "\n";
   master_alert += "Lot: " + DoubleToString(lot, 2);
   SendToMaster(master_alert);
}

void SendDailyReport() {
   double equity = accountInfo.Equity();
   double pnl = equity - daily_start_equity;
   double pnl_pct = (pnl / daily_start_equity) * 100;
   string emoji = (pnl >= 0) ? "🟢" : "🔴";
   SendToClient("📊 <b>รายงานประจำวัน</b>\n\n" +
                "💰 Equity: " + DoubleToString(equity, 2) + "\n" +
                "📈 P/L: " + emoji + " " + DoubleToString(pnl, 2) + " (" + DoubleToString(pnl_pct, 2) + "%)\n" +
                "🎯 เทรด: " + IntegerToString(trades_today) + "\n" +
                "📊 Position: " + IntegerToString(CountOpenPositions()) + "\n" +
                "⚖️ Risk: " + DoubleToString(current_risk_percent, 1) + "%\n" +
                "🔄 " + (trading_enabled ? "✅ กำลังเทรด" : "⏸️ หยุดชั่วคราว"));
}

void StringToLower(string &str) {
   int len = StringLen(str);
   for(int i = 0; i < len; i++) {
      ushort ch = StringGetCharacter(str, i);
      if(ch >= 'A' && ch <= 'Z') StringSetCharacter(str, i, ch + 32);
   }
}

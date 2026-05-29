  #property strict

  #include <Trade/Trade.mqh>

  input string InpApiBase = "http://127.0.0.1:3000";
  input double InpRiskPerTrade = 0.005;
  input int InpBreakoutLookback = 55;
  input int InpAtrPeriod = 20;
  input int InpFastSma = 100;
  input int InpTrendSma = 200;
  input int InpMaxSpreadPips = 50;
  input double InpMaxDailyLossPct = 0.02;
  input bool InpTestMode = false;
  input ENUM_TIMEFRAMES InpTestTimeframe = PERIOD_M1;
  input bool InpTestForceTrade = false;
  input bool InpTestForceBuy = true;
  input double InpTestFixedLots = 0.01;
  input int InpTestStopPips = 20;

  CTrade trade;
  datetime lastBarTime = 0;
  double dailyStartEquity = 0;
  datetime dailyResetTime = 0;

  double CurrentAsk()
  {
    return SymbolInfoDouble(_Symbol, SYMBOL_ASK);
  }

  double CurrentBid()
  {
    return SymbolInfoDouble(_Symbol, SYMBOL_BID);
  }

  double PipSize()
  {
    return (_Digits == 3 || _Digits == 5) ? (_Point * 10.0) : _Point;
  }

  ENUM_TIMEFRAMES EvaluationTimeframe()
  {
    if(InpTestMode)
    {
      return InpTestTimeframe == PERIOD_CURRENT ? (ENUM_TIMEFRAMES)_Period : InpTestTimeframe;
    }

    return PERIOD_D1;
  }

  string EvaluationTimeframeLabel()
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();

    switch(timeframe)
    {
      case PERIOD_M1: return "M1";
      case PERIOD_M2: return "M2";
      case PERIOD_M3: return "M3";
      case PERIOD_M4: return "M4";
      case PERIOD_M5: return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1: return "H1";
      case PERIOD_H4: return "H4";
      case PERIOD_D1: return "D1";
      default: return EnumToString(timeframe);
    }
  }

  string StatusLabelName()
  {
    return "DailyBreakoutEA_Status";
  }

  void UpdateStatusLabel()
  {
    string testSuffix = (InpTestMode && InpTestForceTrade) ? " | FORCE" : "";
    string labelText = "DailyBreakoutEA | Mode: " + (InpTestMode ? "TEST" : "LIVE") + testSuffix + " | TF: " + EvaluationTimeframeLabel();
    color labelColor = InpTestMode ? clrOrange : clrLimeGreen;

    if(ObjectFind(0, StatusLabelName()) < 0)
    {
      ObjectCreate(0, StatusLabelName(), OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_XDISTANCE, 12);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_YDISTANCE, 12);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_FONTSIZE, 11);
      ObjectSetString(0, StatusLabelName(), OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, StatusLabelName(), OBJPROP_BACK, false);
    }

    ObjectSetString(0, StatusLabelName(), OBJPROP_TEXT, labelText);
    ObjectSetInteger(0, StatusLabelName(), OBJPROP_COLOR, labelColor);
  }

  void RemoveStatusLabel()
  {
    ObjectDelete(0, StatusLabelName());
  }

  datetime ToUtc(datetime serverTime)
  {
    return serverTime - (TimeCurrent() - TimeGMT());
  }

  string FormatUtcIso(datetime value)
  {
    MqlDateTime parts;
    TimeToStruct(value, parts);
    return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ", parts.year, parts.mon, parts.day, parts.hour, parts.min, parts.sec);
  }

  string JsonNumber(double value, int digits = 6)
  {
    return DoubleToString(value, digits);
  }

  bool SendBackendJson(string endpoint, string payload, string label)
  {
    string headers = "Content-Type: application/json; charset=utf-8\r\n";
    char data[];
    char result[];
    string responseHeaders;
    int timeout = 5000;
    string url = InpApiBase + endpoint;

    StringToCharArray(payload, data, 0, StringLen(payload));
    int status = WebRequest("POST", url, headers, timeout, data, result, responseHeaders);
    if(status == -1)
    {
      Print("WEBREQUEST FAILED [", label, "] to ", url, " | error=", GetLastError());
      return false;
    }

    string responseBody = CharArrayToString(result);
    Print("WEBREQUEST [", label, "] status=", status, " url=", url, " response=", responseBody);
    return (status >= 200 && status < 300);
  }

  double ReadIndicatorValue(int handle, int shift)
  {
    if(handle == INVALID_HANDLE)
    {
      return 0;
    }

    double values[];
    ArraySetAsSeries(values, true);
    if(CopyBuffer(handle, 0, shift, 1, values) <= 0)
    {
      return 0;
    }

    return values[0];
  }

  double SmaValue(int period, int shift)
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    int handle = iMA(_Symbol, timeframe, period, 0, MODE_SMA, PRICE_CLOSE);
    double value = ReadIndicatorValue(handle, shift);
    if(handle != INVALID_HANDLE)
    {
      IndicatorRelease(handle);
    }

    return value;
  }

  double AtrValue(int period, int shift)
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    int handle = iATR(_Symbol, timeframe, period);
    double value = ReadIndicatorValue(handle, shift);
    if(handle != INVALID_HANDLE)
    {
      IndicatorRelease(handle);
    }

    return value;
  }

  bool IsNewCompletedBar()
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    datetime currentBar = iTime(_Symbol, timeframe, 1);
    if(currentBar == 0)
    {
      return false;
    }

    if(currentBar != lastBarTime)
    {
      lastBarTime = currentBar;
      return true;
    }

    return false;
  }

  double HighestHighLookback()
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    double hh = -DBL_MAX;
    int endShift = InpBreakoutLookback + 1;
    for(int i = 2; i <= endShift; i++)
    {
      double val = iHigh(_Symbol, timeframe, i);
      if(val > hh)
      {
        hh = val;
      }
    }
    return hh;
  }

  double LowestLowLookback()
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    double ll = DBL_MAX;
    int endShift = InpBreakoutLookback + 1;
    for(int i = 2; i <= endShift; i++)
    {
      double val = iLow(_Symbol, timeframe, i);
      if(val < ll)
      {
        ll = val;
      }
    }
    return ll;
  }

  void SendSignalRequest(double close1, double smaFast, double smaTrend, double atr, double hh55, double ll55)
  {
    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    string timeframeLabel = EvaluationTimeframeLabel();
    datetime barCloseUtc = ToUtc(iTime(_Symbol, timeframe, 1));
    double ask = CurrentAsk();
    double bid = CurrentBid();
    double volatility = (close1 > 0) ? (atr / close1) : atr;
    string accountId = IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN));
    string payload =
      "{" +
        "\"decisionId\":\"EA-" + _Symbol + "-" + FormatUtcIso(barCloseUtc) + "\"," +
        "\"strategyId\":\"daily-breakout-5-10\"," +
        "\"strategyVersion\":\"1.0.0\"," +
        "\"symbol\":\"" + _Symbol + "\"," +
        "\"timeframe\":\"" + timeframeLabel + "\"," +
        "\"barCloseTimeUtc\":\"" + FormatUtcIso(barCloseUtc) + "\"," +
        "\"marketSnapshot\":{" +
          "\"symbol\":\"" + _Symbol + "\"," +
          "\"timeframe\":\"" + timeframeLabel + "\"," +
          "\"barCloseTimeUtc\":\"" + FormatUtcIso(barCloseUtc) + "\"," +
          "\"close1\":" + JsonNumber(close1, _Digits) + "," +
          "\"sma100_1\":" + JsonNumber(smaFast, _Digits) + "," +
          "\"sma200_1\":" + JsonNumber(smaTrend, _Digits) + "," +
          "\"highestHigh55\":" + JsonNumber(hh55, _Digits) + "," +
          "\"lowestLow55\":" + JsonNumber(ll55, _Digits) + "," +
          "\"atr20_1\":" + JsonNumber(atr, _Digits) + "," +
          "\"volatility\":" + JsonNumber(volatility, 8) + "," +
          "\"spreadPrice\":" + JsonNumber(ask - bid, _Digits) + "," +
          "\"open0\":" + JsonNumber(iOpen(_Symbol, timeframe, 0), _Digits) + "," +
          "\"close1Prev\":" + JsonNumber(iClose(_Symbol, timeframe, 2), _Digits) +
        "}," +
        "\"accountSnapshot\":{" +
          "\"accountId\":\"" + accountId + "\"," +
          "\"equity\":" + JsonNumber(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "," +
          "\"balance\":" + JsonNumber(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "," +
          "\"openRisk\":" + JsonNumber(MathMax(AccountInfoDouble(ACCOUNT_EQUITY) - AccountInfoDouble(ACCOUNT_MARGIN_FREE), 0.0) / MathMax(AccountInfoDouble(ACCOUNT_EQUITY), 1.0), 6) + "," +
          "\"openTrades\":" + IntegerToString(PositionsTotal()) + "," +
          "\"dailyLossPct\":" + JsonNumber((dailyStartEquity > 0 ? (dailyStartEquity - AccountInfoDouble(ACCOUNT_EQUITY)) / dailyStartEquity : 0), 6) + "," +
          "\"weeklyLossPct\":0" +
        "}" +
      "}";

    SendBackendJson("/signal", payload, "signal");
  }

  void SendOpenTradesSnapshot()
  {
    string payload = "{\"symbol\":\"" + _Symbol + "\",\"capturedAtUtc\":\"" + FormatUtcIso(ToUtc(TimeCurrent())) + "\",\"payload\":{\"positionsTotal\":" + IntegerToString(PositionsTotal()) + "}}";
    SendBackendJson("/trades/open", payload, "open-trades");
  }

  bool HasExistingPosition()
  {
    for(int i = 0; i < PositionsTotal(); i++)
    {
      if(PositionGetSymbol(i) == _Symbol)
      {
        return true;
      }
    }
    return false;
  }

  bool CheckSafetyPreconditions()
  {
    double ask = CurrentAsk();
    double bid = CurrentBid();
    int spreadPips = (int)MathRound((ask - bid) / PipSize());
    if(spreadPips > InpMaxSpreadPips)
    {
      Print("SAFETY: Spread ", spreadPips, " exceeds max ", InpMaxSpreadPips);
      return false;
    }

    double dailyLoss = dailyStartEquity - AccountInfoDouble(ACCOUNT_EQUITY);
    double lossRatio = (dailyStartEquity > 0) ? (dailyLoss / dailyStartEquity) : 0;
    if(lossRatio > InpMaxDailyLossPct)
    {
      Print("SAFETY: Daily loss ", DoubleToString(lossRatio * 100, 2), "% exceeds limit ", InpMaxDailyLossPct * 100, "%");
      return false;
    }

    ENUM_SYMBOL_TRADE_MODE tradeMode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE);
    if(tradeMode == SYMBOL_TRADE_MODE_DISABLED || tradeMode == SYMBOL_TRADE_MODE_CLOSEONLY)
    {
      Print("SAFETY: Symbol trade mode blocks new entries");
      return false;
    }

    if(ask <= 0 || bid <= 0)
    {
      Print("SAFETY: Symbol not tradeable or quotes unavailable");
      return false;
    }

    double minMarginRequired = SymbolInfoDouble(_Symbol, SYMBOL_MARGIN_INITIAL);
    double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
    if(freeMargin < minMarginRequired * 1.5)
    {
      Print("SAFETY: Insufficient free margin (", freeMargin, " vs required ", minMarginRequired * 1.5, ")");
      return false;
    }

    return true;
  }

  double NormalizeLots(double lots)
  {
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    if(lotStep > 0)
    {
      lots = MathFloor(lots / lotStep) * lotStep;
    }

    if(lots < minLot)
    {
      return 0;
    }

    if(lots > maxLot)
    {
      lots = maxLot;
    }

    return lots;
  }

  double MinSymbolLot()
  {
    return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
  }

  double LotStep()
  {
    return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
  }

  double CalcPositionSize(double stopDistancePips, double riskAmount)
  {
    if(stopDistancePips <= 0)
    {
      Print("ERROR: Invalid stop distance ", stopDistancePips);
      return 0;
    }

    double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
    double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double pointValue = (tickSize > 0) ? (tickValue * (_Point / tickSize)) : 0;

    if(pointValue <= 0)
    {
      Print("ERROR: Invalid point value ", pointValue);
      return 0;
    }

    double lots = riskAmount / (stopDistancePips * pointValue);
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    if(lots < minLot)
    {
      Print("VALIDATION: Calculated lots ", DoubleToString(lots, 2), " below min ", DoubleToString(minLot, 2));
      return 0;
    }

    if(lots > maxLot)
    {
      lots = maxLot;
    }

    if(lotStep > 0)
    {
      lots = MathFloor(lots / lotStep) * lotStep;
    }

    double marginRequired = 0;
    if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lots, CurrentAsk(), marginRequired))
    {
      double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if(marginRequired > freeMargin)
      {
        double marginPerLot = (lots > 0) ? (marginRequired / lots) : 0;
        if(marginPerLot <= 0)
        {
          Print("ERROR: Invalid margin-per-lot calculation");
          return 0;
        }

        double cappedLots = freeMargin / (marginPerLot * 1.5);
        if(lotStep > 0)
        {
          cappedLots = MathFloor(cappedLots / lotStep) * lotStep;
        }

        if(cappedLots < minLot)
        {
          Print("VALIDATION: Margin cap pushed lots below minimum lot size");
          return 0;
        }

        Print("VALIDATION: Capping lots from ", DoubleToString(lots, 2), " to ", DoubleToString(cappedLots, 2), " based on free margin ", DoubleToString(freeMargin, 2));
        lots = MathMin(cappedLots, maxLot);
      }
    }

    Print("Position sizing: risk=", riskAmount, " stop=", stopDistancePips, "pips => lots=", DoubleToString(lots, 2));
    return lots;
  }

  bool ExecuteTrade(string direction, double lots, double stopDistancePips, double atr)
  {
    if(!CheckSafetyPreconditions())
    {
      Print("Trade rejected: safety preconditions failed");
      return false;
    }

    double entryPrice = (direction == "BUY") ? CurrentAsk() : CurrentBid();
    double pipSize = PipSize();
    double stopPrice = (direction == "BUY") ? (entryPrice - stopDistancePips * pipSize) : (entryPrice + stopDistancePips * pipSize);
    double takeProfit = (direction == "BUY") ? (entryPrice + (stopDistancePips * 2) * pipSize) : (entryPrice - (stopDistancePips * 2) * pipSize);
    ENUM_ORDER_TYPE orderType = (direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    double marginRequired = 0;
    bool marginOk = OrderCalcMargin(orderType, _Symbol, lots, entryPrice, marginRequired);

    Print("ORDER PREVIEW: direction=", direction,
          " lots=", DoubleToString(lots, 2),
          " entry=", DoubleToString(entryPrice, _Digits),
          " stop=", DoubleToString(stopPrice, _Digits),
          " tp=", DoubleToString(takeProfit, _Digits),
          " margin=", (marginOk ? DoubleToString(marginRequired, 2) : "n/a"),
          " freeMargin=", DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));

    Print("Executing ", direction, " @ ", entryPrice, " | Stop: ", stopPrice, " | TP: ", takeProfit, " | Lots: ", DoubleToString(lots, 2));

    if(direction == "BUY")
    {
      if(!trade.Buy(lots, _Symbol, entryPrice, stopPrice, takeProfit, "DailyBreakout"))
      {
        Print("BUY order failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
        return false;
      }
    }
    else if(direction == "SELL")
    {
      if(!trade.Sell(lots, _Symbol, entryPrice, stopPrice, takeProfit, "DailyBreakout"))
      {
        Print("SELL order failed: ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
        return false;
      }
    }

    SendOpenTradesSnapshot();
    return true;
  }

  int OnInit()
  {
    Print("DailyBreakoutEA initialized");
    if(InpTestMode)
    {
      Print("TEST MODE enabled on timeframe ", EvaluationTimeframeLabel());
      if(InpTestForceTrade)
      {
        Print("TEST MODE force trade enabled: direction=", (InpTestForceBuy ? "BUY" : "SELL"), " lots=", DoubleToString(InpTestFixedLots, 2), " stopPips=", InpTestStopPips);
      }
    }
    Print("Risk per trade: ", InpRiskPerTrade * 100, "%");
    Print("Max daily loss: ", InpMaxDailyLossPct * 100, "%");
    Print("Max spread: ", InpMaxSpreadPips, " pips");
    UpdateStatusLabel();

    dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    dailyResetTime = iTime(_Symbol, PERIOD_D1, 0);

    return(INIT_SUCCEEDED);
  }

  void OnDeinit(const int reason)
  {
    RemoveStatusLabel();
  }

  void OnTick()
  {
    UpdateStatusLabel();

    if(!IsNewCompletedBar())
    {
      return;
    }

    ENUM_TIMEFRAMES timeframe = EvaluationTimeframe();
    datetime currentRiskResetTime = iTime(_Symbol, PERIOD_D1, 0);
    if(currentRiskResetTime != dailyResetTime)
    {
      dailyResetTime = currentRiskResetTime;
      dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      Print("Daily risk reset: equity=", DoubleToString(dailyStartEquity, 2));
    }

    double close1 = iClose(_Symbol, timeframe, 1);
    double smaTrend = SmaValue(InpTrendSma, 1);
    double smaFast = SmaValue(InpFastSma, 1);
    double atr = AtrValue(InpAtrPeriod, 1);
    double hh55 = HighestHighLookback();
    double ll55 = LowestLowLookback();

    if(smaTrend <= 0 || smaFast <= 0 || atr <= 0)
    {
      Print("Indicator values unavailable - skipping bar");
      return;
    }

    SendSignalRequest(close1, smaFast, smaTrend, atr, hh55, ll55);

    bool hasPosition = HasExistingPosition();
    if(hasPosition)
    {
      Print("Position exists for ", _Symbol, " - skipping entry");
      SendOpenTradesSnapshot();
      return;
    }

    if(InpTestMode && InpTestForceTrade)
    {
      double forceLots = NormalizeLots(InpTestFixedLots);
      double minLot = MinSymbolLot();
      double lotStep = LotStep();

      if(forceLots <= 0 && InpTestFixedLots > 0 && InpTestFixedLots < minLot)
      {
        // TEST-only behavior: if configured lots are too small for broker constraints, bump to minimum lot.
        forceLots = NormalizeLots(minLot);
        Print("TEST MODE adjusted fixed lots from ", DoubleToString(InpTestFixedLots, 2),
              " to broker minimum ", DoubleToString(forceLots, 2),
              " (minLot=", DoubleToString(minLot, 2), ", step=", DoubleToString(lotStep, 2), ")");
      }

      if(forceLots <= 0)
      {
        Print("TEST MODE force trade rejected: invalid fixed lot size ", DoubleToString(InpTestFixedLots, 2),
              " (minLot=", DoubleToString(minLot, 2), ", step=", DoubleToString(lotStep, 2), ")");
        SendOpenTradesSnapshot();
        return;
      }

      double forceStopPips = (InpTestStopPips > 0) ? (double)InpTestStopPips : 10.0;
      string forceDirection = InpTestForceBuy ? "BUY" : "SELL";
      Print("TEST MODE forcing ", forceDirection, " with lots=", DoubleToString(forceLots, 2), " stopPips=", DoubleToString(forceStopPips, 1));

      bool forcedTradeOk = ExecuteTrade(forceDirection, forceLots, forceStopPips, atr);
      if(!forcedTradeOk)
      {
        SendOpenTradesSnapshot();
      }
      return;
    }

    bool longSignal = (close1 > smaTrend && close1 > hh55);
    bool shortSignal = (close1 < smaTrend && close1 < ll55);

    if(longSignal)
    {
      Print("=== LONG SETUP DETECTED ===");
      double stopDistancePips = (close1 - ll55) / PipSize();
      double riskAmount = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPerTrade;
      double lots = CalcPositionSize(stopDistancePips, riskAmount);

      if(lots > 0)
      {
        ExecuteTrade("BUY", lots, stopDistancePips, atr);
      }
      else
      {
        Print("LONG setup rejected: invalid lot size");
      }
    }
    else if(shortSignal)
    {
      Print("=== SHORT SETUP DETECTED ===");
      double stopDistancePips = (hh55 - close1) / PipSize();
      double riskAmount = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPerTrade;
      double lots = CalcPositionSize(stopDistancePips, riskAmount);

      if(lots > 0)
      {
        ExecuteTrade("SELL", lots, stopDistancePips, atr);
      }
      else
      {
        Print("SHORT setup rejected: invalid lot size");
      }
    }
    else
    {
      Print("No setup: ", _Symbol, " close=", close1, " sma200=", smaTrend, " sma100=", smaFast, " atr=", atr);
    }

    SendOpenTradesSnapshot();
  }

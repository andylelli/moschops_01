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
  int handle = iMA(_Symbol, PERIOD_D1, period, 0, MODE_SMA, PRICE_CLOSE);
  double value = ReadIndicatorValue(handle, shift);
  if(handle != INVALID_HANDLE)
  {
    IndicatorRelease(handle);
  }

  return value;
}

double AtrValue(int period, int shift)
{
  int handle = iATR(_Symbol, PERIOD_D1, period);
  double value = ReadIndicatorValue(handle, shift);
  if(handle != INVALID_HANDLE)
  {
    IndicatorRelease(handle);
  }

  return value;
}

bool IsNewCompletedBar()
{
  datetime currentBar = iTime(_Symbol, PERIOD_D1, 1);
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
  double hh = -DBL_MAX;
  int endShift = InpBreakoutLookback + 1;
  for(int i = 2; i <= endShift; i++)
  {
    double val = iHigh(_Symbol, PERIOD_D1, i);
    if(val > hh)
    {
      hh = val;
    }
  }
  return hh;
}

double LowestLowLookback()
{
  double ll = DBL_MAX;
  int endShift = InpBreakoutLookback + 1;
  for(int i = 2; i <= endShift; i++)
  {
    double val = iLow(_Symbol, PERIOD_D1, i);
    if(val < ll)
    {
      ll = val;
    }
  }
  return ll;
}

void SendOpenTradesSnapshot()
{
  string payload = "{\"symbol\":\"" + _Symbol + "\",\"capturedAtUtc\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\",\"payload\":{\"positionsTotal\":" + IntegerToString(PositionsTotal()) + "}}";
  string headers = "Content-Type: application/json\r\n";
  char data[];
  char result[];
  StringToCharArray(payload, data);
  string responseHeaders;
  int timeout = 5000;

  string url = InpApiBase + "/trades/open";
  WebRequest("POST", url, headers, timeout, data, result, responseHeaders);
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
  int spreadPips = (int)((ask - bid) / _Point);
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

double CalcPositionSize(double stopDistancePips, double riskAmount)
{
  if(stopDistancePips <= 0)
  {
    Print("ERROR: Invalid stop distance ", stopDistancePips);
    return 0;
  }

  double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
  double pipValue = tickValue * _Point * 10;

  if(pipValue <= 0)
  {
    Print("ERROR: Invalid pip value ", pipValue);
    return 0;
  }

  double lots = riskAmount / (stopDistancePips * pipValue);
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
  double stopPrice = (direction == "BUY") ? (entryPrice - stopDistancePips * _Point) : (entryPrice + stopDistancePips * _Point);
  double takeProfit = (direction == "BUY") ? (entryPrice + (stopDistancePips * 2) * _Point) : (entryPrice - (stopDistancePips * 2) * _Point);

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
  Print("Risk per trade: ", InpRiskPerTrade * 100, "%");
  Print("Max daily loss: ", InpMaxDailyLossPct * 100, "%");
  Print("Max spread: ", InpMaxSpreadPips, " pips");
  
  dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
  dailyResetTime = iTime(_Symbol, PERIOD_D1, 0);
  
  return(INIT_SUCCEEDED);
}

void OnTick()
{
  if(!IsNewCompletedBar())
  {
    return;
  }

  datetime currentDayTime = iTime(_Symbol, PERIOD_D1, 0);
  if(currentDayTime != dailyResetTime)
  {
    dailyResetTime = currentDayTime;
    dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    Print("Daily reset: equity=", DoubleToString(dailyStartEquity, 2));
  }

  double close1 = iClose(_Symbol, PERIOD_D1, 1);
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

  bool hasPosition = HasExistingPosition();
  if(hasPosition)
  {
    Print("Position exists for ", _Symbol, " - skipping entry");
    SendOpenTradesSnapshot();
    return;
  }

  bool longSignal = (close1 > smaTrend && close1 > hh55);
  bool shortSignal = (close1 < smaTrend && close1 < ll55);

  if(longSignal)
  {
    Print("=== LONG SETUP DETECTED ===");
    double stopDistancePips = (close1 - ll55) / _Point;
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
    double stopDistancePips = (hh55 - close1) / _Point;
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

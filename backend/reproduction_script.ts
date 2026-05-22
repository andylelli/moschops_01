import { buildApp } from './src/app';
import { prismaClient } from './src/services/prisma';

async function run() {
  const app = buildApp();
  await app.ready();
  
  const decisionId = 'test-decision-' + Date.now();
  const payload = {
    decisionId,
    strategyId: 'test-strategy',
    strategyVersion: '1.0.0',
    symbol: 'EURUSD',
    timeframe: 'H1',
    barCloseTimeUtc: new Date().toISOString(),
    marketSnapshot: {
      symbol: 'EURUSD',
      timeframe: 'H1',
      barCloseTimeUtc: new Date().toISOString(),
      close1: 1.1000,
      sma100_1: 1.0900,
      sma200_1: 1.0800,
      highestHigh55: 1.1100,
      lowestLow55: 1.0700,
      atr20_1: 0.0010,
      volatility: 0.0005
    },
    accountSnapshot: {
      accountId: 'test-account',
      equity: 10000,
      balance: 10000,
      openRisk: 100,
      openTrades: 1,
      dailyLossPct: 0.1,
      weeklyLossPct: 0.2
    }
  };

  const res1 = await app.inject({
    method: 'POST',
    url: '/signal',
    payload
  });

  const res2 = await app.inject({
    method: 'POST',
    url: '/signal',
    payload
  });

  console.log('STATUS_FIRST', res1.statusCode);
  console.log('STATUS_REPLAY', res2.statusCode);
  
  const body1 = JSON.parse(res1.body);
  const body2 = JSON.parse(res2.body);

  console.log('BODY_FIRST', JSON.stringify(body1));
  console.log('BODY_REPLAY', JSON.stringify(body2));

  console.log('MATCH=' + (JSON.stringify(body1) === JSON.stringify(body2)));

  try {
    await prismaClient().$disconnect();
  } catch (e) {}
  await app.close();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});

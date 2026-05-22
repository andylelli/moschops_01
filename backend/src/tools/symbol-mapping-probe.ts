import { writeFile } from "node:fs/promises";
import path from "node:path";
import { getSymbolCurrencyExposure, parseEnabledSymbols } from "../services/news-domain";

async function main(): Promise<void> {
  const symbols = parseEnabledSymbols();

  const items = symbols.map((symbol) => ({
    symbol,
    currencies: getSymbolCurrencyExposure(symbol),
  }));

  const missing = items.filter((item) => item.currencies.length !== 2).map((item) => item.symbol);

  const report = {
    generatedAtUtc: new Date().toISOString(),
    symbolCount: items.length,
    mappedCount: items.length - missing.length,
    missingCount: missing.length,
    missingSymbols: missing,
    items,
    status: missing.length === 0 ? "pass" : "fail",
  };

  await writeFile(path.resolve(process.cwd(), "symbol_mapping_report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(`RESULT:${JSON.stringify({ status: report.status, mappedCount: report.mappedCount, missingCount: report.missingCount })}`);
}

void main();

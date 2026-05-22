import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { RUNTIME_FEATURE_SCHEMA } from "../services/feature-schema";

interface FeatureSchemaContract {
  schemaVersion: string;
  features: string[];
}

function hashFeatures(features: readonly string[]): string {
  return createHash("sha256").update(JSON.stringify(features)).digest("hex");
}

async function main(): Promise<void> {
  const contractPath = path.resolve(process.cwd(), "../models/feature_schema_v1.json");
  const contractRaw = await readFile(contractPath, "utf8");
  const contract = JSON.parse(contractRaw) as FeatureSchemaContract;

  const runtimeFeatures = [...RUNTIME_FEATURE_SCHEMA];
  const contractFeatures = [...contract.features];
  const matches = JSON.stringify(runtimeFeatures) === JSON.stringify(contractFeatures);

  const report = {
    generatedAtUtc: new Date().toISOString(),
    schemaVersion: contract.schemaVersion,
    runtimeFeatures,
    contractFeatures,
    runtimeHash: hashFeatures(runtimeFeatures),
    contractHash: hashFeatures(contractFeatures),
    status: matches ? "pass" : "fail",
  };

  await writeFile(path.resolve(process.cwd(), "feature_schema_report.json"), JSON.stringify(report, null, 2), "utf8");
  console.log(`RESULT:${JSON.stringify({ status: report.status, runtimeHash: report.runtimeHash, contractHash: report.contractHash })}`);
}

void main();

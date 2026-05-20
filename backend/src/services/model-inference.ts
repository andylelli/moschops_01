import fs from "node:fs";
import path from "node:path";
import * as ort from "onnxruntime-node";

let session: ort.InferenceSession | null = null;
let modelLoadError: Error | null = null;
let modelReady = false;
let lastInferenceError: string | null = null;

export type InferenceStatus =
  | "APPLIED"
  | "MODEL_UNAVAILABLE"
  | "INVALID_FEATURES"
  | "INVALID_OUTPUT"
  | "INFERENCE_ERROR";

export interface InferenceResult {
  score: number | null;
  status: InferenceStatus;
}

export interface ModelLoaderStatus {
  state: "available" | "degraded";
  reason?: string;
}

/**
 * Get or load the ONNX inference session.
 * Lazy-loads model on first call; caches for reuse.
 *
 * @returns InferenceSession if model loaded; null if unavailable or error
 */
async function getSession(): Promise<ort.InferenceSession | null> {
  // Return null if we already tried and failed
  if (modelLoadError) {
    return null;
  }

  if (session) {
    return session;
  }

  const modelPath = path.resolve(process.cwd(), "../models/daily_breakout_model.onnx");

  // Check file exists
  if (!fs.existsSync(modelPath)) {
    const error = new Error(`Model file not found: ${modelPath}`);
    modelLoadError = error;
    console.error("MODEL_LOAD_FAILED:", {
      code: "FILE_NOT_FOUND",
      path: modelPath,
      message: error.message,
    });
    return null;
  }

  try {
    console.log("Loading ONNX model from:", modelPath);
    session = await ort.InferenceSession.create(modelPath);
    console.log("MODEL_LOAD_SUCCESS:", {
      path: modelPath,
      inputs: session.inputNames,
      outputs: session.outputNames,
    });
    return session;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    modelLoadError = err;
    console.error("MODEL_LOAD_FAILED:", {
      code: "LOAD_ERROR",
      path: modelPath,
      error: err.message,
      stack: err.stack,
    });
    return null;
  }
}

function parseProbability(active: ort.InferenceSession, outputs: Record<string, ort.Tensor>): number | null {
  const probabilityOutputName =
    active.outputNames.find((name) => /prob/i.test(name)) ?? active.outputNames[active.outputNames.length - 1];
  const outputTensor = outputs[probabilityOutputName];
  if (!outputTensor || !("data" in outputTensor)) {
    return null;
  }

  const values = Array.from(outputTensor.data as ArrayLike<number>);
  const score = values.length > 1 ? Number(values[1]) : Number(values[0] ?? 0);
  if (!Number.isFinite(score) || score < 0 || score > 1) {
    return null;
  }

  return score;
}

export async function preflightModelInference(): Promise<void> {
  const active = await getSession();
  if (!active) {
    modelReady = false;
    return;
  }

  try {
    const inputName = active.inputNames[0];
    const probabilityOutputName =
      active.outputNames.find((name) => /prob/i.test(name)) ?? active.outputNames[active.outputNames.length - 1];
    const warmup = new ort.Tensor("float32", Float32Array.from([0, 1, 0.05, 0, 0]), [1, 5]);
    const outputs = await active.run({ [inputName]: warmup }, [probabilityOutputName]);
    const score = parseProbability(active, outputs as Record<string, ort.Tensor>);

    if (score === null) {
      modelReady = false;
      lastInferenceError = "invalid_warmup_output";
      console.error("MODEL_LOAD_FAILED:", {
        code: "INVALID_WARMUP_OUTPUT",
        outputNames: active.outputNames,
      });
      return;
    }

    modelReady = true;
    lastInferenceError = null;
    console.log("MODEL_PREFLIGHT_OK:", { outputNames: active.outputNames });
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    modelLoadError = err;
    modelReady = false;
    lastInferenceError = err.message;
    console.error("MODEL_LOAD_FAILED:", {
      code: "PREFLIGHT_ERROR",
      error: err.message,
    });
  }
}

export function getModelLoaderStatus(): ModelLoaderStatus {
  if (modelReady && !modelLoadError) {
    return { state: "available" };
  }

  return {
    state: "degraded",
    reason: modelLoadError?.message ?? lastInferenceError ?? "model_not_ready",
  };
}

/**
 * Infer AI score for a trade signal using ONNX model.
 *
 * @param features 5-element array: [trend_strength, volatility, spread_atr, breakout_distance, momentum]
 * @returns Probability score in [0, 1]; null if model unavailable
 *
 * @throws Never throws; returns null on any inference error
 */
export async function inferScore(features: number[]): Promise<InferenceResult> {
  const active = await getSession();
  if (!active) {
    if (modelLoadError) {
      console.warn("INFERENCE_SKIPPED:", {
        reason: "model_load_failed",
        error: modelLoadError.message,
      });
    }
    return { score: null, status: "MODEL_UNAVAILABLE" };
  }

  if (!modelReady) {
    return { score: null, status: "MODEL_UNAVAILABLE" };
  }

  try {
    // Validate features
    if (!Array.isArray(features) || features.length !== 5) {
      console.warn("INFERENCE_SKIPPED:", {
        reason: "invalid_features",
        count: features.length,
        expected: 5,
      });
      return { score: null, status: "INVALID_FEATURES" };
    }

    // Check for NaN or Infinity
    if (!features.every((f) => Number.isFinite(f))) {
      console.warn("INFERENCE_SKIPPED:", {
        reason: "non_finite_features",
        features,
      });
      return { score: null, status: "INVALID_FEATURES" };
    }

    const inputName = active.inputNames[0];
    const probabilityOutputName =
      active.outputNames.find((name) => /prob/i.test(name)) ?? active.outputNames[active.outputNames.length - 1];
    const tensor = new ort.Tensor("float32", Float32Array.from(features), [1, features.length]);
    const outputs = await active.run({ [inputName]: tensor }, [probabilityOutputName]);
    const score = parseProbability(active, outputs as Record<string, ort.Tensor>);

    if (score === null) {
      console.warn("INFERENCE_SKIPPED:", {
        reason: "invalid_output",
        outputNames: active.outputNames,
      });
      return { score: null, status: "INVALID_OUTPUT" };
    }

    return { score, status: "APPLIED" };
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    lastInferenceError = err.message;

    // onnxruntime-node cannot consume some non-tensor output types; fail closed and stop retrying.
    if (err.message.includes("Non tensor type is temporarily not supported")) {
      modelLoadError = err;
      modelReady = false;
      console.error("MODEL_LOAD_FAILED:", {
        code: "UNSUPPORTED_MODEL_OUTPUT",
        error: err.message,
      });
      return { score: null, status: "MODEL_UNAVAILABLE" };
    }

    console.error("INFERENCE_ERROR:", {
      error: err.message,
      features,
      stack: err.stack,
    });
    return { score: null, status: "INFERENCE_ERROR" };
  }
}

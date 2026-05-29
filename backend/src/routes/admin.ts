import type { FastifyInstance } from "fastify";
import type { Prisma } from "@prisma/client";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { recordFileLog } from "../services/file-log";

const ADMIN_EVENT_APPROVAL_SUBMITTED = "ADMIN_APPROVAL_SUBMITTED";
const ADMIN_EVENT_APPROVAL_DECIDED = "ADMIN_APPROVAL_DECIDED";
const ADMIN_EVENT_CONFIG_ROLLBACK = "ADMIN_CONFIG_ROLLBACK";

const approvalDecisionSchema = z.object({
  actor: z.string().min(1),
  reason: z.string().min(10),
});

const submitApprovalSchema = z.object({
  actionType: z.string().min(1),
  actionLabel: z.string().min(3),
  owner: z.string().min(1),
  scope: z.string().min(1),
  requestedBy: z.string().min(1),
  reason: z.string().min(10),
  strategyId: z.string().min(1).optional(),
  strategyVersion: z.string().min(1).optional(),
});

const listApprovalsSchema = z.object({
  state: z.enum(["PENDING", "APPROVED", "REJECTED", "ALL"]).default("ALL"),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

const listAuditSchema = z.object({
  actor: z.string().optional(),
  actionType: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(500).default(100),
});

const listSnapshotsSchema = z.object({
  strategyId: z.string().min(1).default("daily-breakout-5-10"),
  strategyVersion: z.string().min(1).default("1.0.0"),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

const rollbackSchema = z.object({
  configId: z.string().min(1),
  actor: z.string().min(1),
  reason: z.string().min(10),
});

type ApprovalState = "PENDING" | "APPROVED" | "REJECTED";

type ApprovalRow = {
  approvalId: string;
  actionType: string;
  actionLabel: string;
  owner: string;
  scope: string;
  requestedBy: string;
  requestedAtUtc: string;
  state: ApprovalState;
  decisionActor: string | null;
  decisionReason: string | null;
  decidedAtUtc: string | null;
  strategyId: string | null;
  strategyVersion: string | null;
};

type AdminAuditRow = {
  eventId: string;
  eventType: string;
  reasonCode: string;
  severity: string;
  actor: string | null;
  actionType: string | null;
  reason: string | null;
  createdAtUtc: string;
  details: unknown;
};

function createApprovalId(): string {
  return `APR-${Date.now()}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
}

function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {};
}

function toApprovalState(value: unknown): ApprovalState {
  if (value === "APPROVED" || value === "REJECTED") {
    return value;
  }

  return "PENDING";
}

async function approvalExists(approvalId: string): Promise<boolean> {
  const existing = await prismaClient().riskEvent.findFirst({
    where: {
      eventType: ADMIN_EVENT_APPROVAL_SUBMITTED,
      detailsJson: {
        path: ["approvalId"],
        equals: approvalId,
      },
    },
    select: { id: true },
  });

  return Boolean(existing);
}

async function approvalAlreadyDecided(approvalId: string): Promise<boolean> {
  const existingDecision = await prismaClient().riskEvent.findFirst({
    where: {
      eventType: ADMIN_EVENT_APPROVAL_DECIDED,
      detailsJson: {
        path: ["approvalId"],
        equals: approvalId,
      },
    },
    select: { id: true },
  });

  return Boolean(existingDecision);
}

async function loadApprovals(limit: number): Promise<ApprovalRow[]> {
  const events = await prismaClient().riskEvent.findMany({
    where: {
      eventType: {
        in: [ADMIN_EVENT_APPROVAL_SUBMITTED, ADMIN_EVENT_APPROVAL_DECIDED],
      },
    },
    orderBy: { createdAt: "desc" },
    take: Math.max(limit * 4, 120),
  });

  const submissionMap = new Map<string, ApprovalRow>();
  const decisionMap = new Map<string, { state: ApprovalState; actor: string | null; reason: string | null; decidedAtUtc: string }>();

  for (const event of events) {
    const details = asObject(event.detailsJson);
    const approvalId = typeof details.approvalId === "string" ? details.approvalId : null;
    if (!approvalId) {
      continue;
    }

    if (event.eventType === ADMIN_EVENT_APPROVAL_SUBMITTED) {
      if (!submissionMap.has(approvalId)) {
        submissionMap.set(approvalId, {
          approvalId,
          actionType: typeof details.actionType === "string" ? details.actionType : "UNKNOWN",
          actionLabel: typeof details.actionLabel === "string" ? details.actionLabel : "Unknown action",
          owner: typeof details.owner === "string" ? details.owner : "unknown",
          scope: typeof details.scope === "string" ? details.scope : "unknown",
          requestedBy: typeof details.requestedBy === "string" ? details.requestedBy : "unknown",
          requestedAtUtc: event.createdAt.toISOString(),
          state: "PENDING",
          decisionActor: null,
          decisionReason: null,
          decidedAtUtc: null,
          strategyId: typeof details.strategyId === "string" ? details.strategyId : null,
          strategyVersion: typeof details.strategyVersion === "string" ? details.strategyVersion : null,
        });
      }
      continue;
    }

    if (!decisionMap.has(approvalId)) {
      decisionMap.set(approvalId, {
        state: toApprovalState(details.decision),
        actor: typeof details.actor === "string" ? details.actor : null,
        reason: typeof details.reason === "string" ? details.reason : null,
        decidedAtUtc: event.createdAt.toISOString(),
      });
    }
  }

  const approvals = Array.from(submissionMap.values()).map((row) => {
    const decision = decisionMap.get(row.approvalId);
    if (!decision) {
      return row;
    }

    return {
      ...row,
      state: decision.state,
      decisionActor: decision.actor,
      decisionReason: decision.reason,
      decidedAtUtc: decision.decidedAtUtc,
    };
  });

  return approvals.sort((a, b) => Date.parse(b.requestedAtUtc) - Date.parse(a.requestedAtUtc)).slice(0, limit);
}

async function resolveApproval(approvalId: string, decision: "APPROVED" | "REJECTED", actor: string, reason: string): Promise<ApprovalRow | null> {
  await prismaClient().riskEvent.create({
    data: {
      strategyId: "admin",
      eventType: ADMIN_EVENT_APPROVAL_DECIDED,
      reasonCode: decision === "APPROVED" ? "APPROVAL_APPROVED" : "APPROVAL_REJECTED",
      severity: decision === "APPROVED" ? "info" : "warning",
      detailsJson: {
        approvalId,
        decision,
        actor,
        reason,
      },
    },
  });

  const approvals = await loadApprovals(200);
  return approvals.find((item) => item.approvalId === approvalId) ?? null;
}

export async function adminRoutes(app: FastifyInstance): Promise<void> {
  app.get("/admin/approvals", async (req, reply) => {
    const parsed = listApprovalsSchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const approvals = await loadApprovals(parsed.data.limit);
    const filtered = parsed.data.state === "ALL" ? approvals : approvals.filter((item) => item.state === parsed.data.state);

    return {
      count: filtered.length,
      items: filtered,
    };
  });

  app.post("/admin/approvals/submit", async (req, reply) => {
    const parsed = submitApprovalSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const approvalId = createApprovalId();
    const payload = parsed.data;

    await prismaClient().riskEvent.create({
      data: {
        strategyId: payload.strategyId ?? "admin",
        eventType: ADMIN_EVENT_APPROVAL_SUBMITTED,
        reasonCode: "APPROVAL_PENDING",
        severity: "warning",
        detailsJson: {
          approvalId,
          actionType: payload.actionType,
          actionLabel: payload.actionLabel,
          owner: payload.owner,
          scope: payload.scope,
          requestedBy: payload.requestedBy,
          reason: payload.reason,
          strategyId: payload.strategyId ?? null,
          strategyVersion: payload.strategyVersion ?? null,
        },
      },
    });

    recordFileLog({
      category: "security",
      level: "warn",
      event: "admin_approval_submitted",
      message: "Administrative approval submitted",
      context: {
        approvalId,
        actionType: payload.actionType,
        actionLabel: payload.actionLabel,
        owner: payload.owner,
        scope: payload.scope,
        requestedBy: payload.requestedBy,
        strategyId: payload.strategyId ?? null,
        strategyVersion: payload.strategyVersion ?? null,
      },
    });

    const approvals = await loadApprovals(200);
    const approval = approvals.find((item) => item.approvalId === approvalId) ?? null;

    return {
      ok: true,
      approval,
    };
  });

  app.post("/admin/approvals/:approvalId/approve", async (req, reply) => {
    const params = z.object({ approvalId: z.string().min(1) }).safeParse(req.params);
    if (!params.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: params.error.message } });
    }

    const body = approvalDecisionSchema.safeParse(req.body);
    if (!body.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: body.error.message } });
    }

    if (!(await approvalExists(params.data.approvalId))) {
      return reply.status(404).send({ error: { code: "NOT_FOUND", message: "Approval request not found" } });
    }

    if (await approvalAlreadyDecided(params.data.approvalId)) {
      return reply.status(409).send({ error: { code: "ALREADY_DECIDED", message: "Approval request is already resolved" } });
    }

    const approval = await resolveApproval(params.data.approvalId, "APPROVED", body.data.actor, body.data.reason);
    recordFileLog({
      category: "security",
      level: "info",
      event: "admin_approval_decided",
      message: "Administrative approval approved",
      context: { approvalId: params.data.approvalId, decision: "APPROVED", actor: body.data.actor },
    });
    return {
      ok: true,
      approval,
    };
  });

  app.post("/admin/approvals/:approvalId/reject", async (req, reply) => {
    const params = z.object({ approvalId: z.string().min(1) }).safeParse(req.params);
    if (!params.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: params.error.message } });
    }

    const body = approvalDecisionSchema.safeParse(req.body);
    if (!body.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: body.error.message } });
    }

    if (!(await approvalExists(params.data.approvalId))) {
      return reply.status(404).send({ error: { code: "NOT_FOUND", message: "Approval request not found" } });
    }

    if (await approvalAlreadyDecided(params.data.approvalId)) {
      return reply.status(409).send({ error: { code: "ALREADY_DECIDED", message: "Approval request is already resolved" } });
    }

    const approval = await resolveApproval(params.data.approvalId, "REJECTED", body.data.actor, body.data.reason);
    recordFileLog({
      category: "security",
      level: "warn",
      event: "admin_approval_decided",
      message: "Administrative approval rejected",
      context: { approvalId: params.data.approvalId, decision: "REJECTED", actor: body.data.actor },
    });
    return {
      ok: true,
      approval,
    };
  });

  app.get("/admin/audit-log", async (req, reply) => {
    const parsed = listAuditSchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const events = await prismaClient().riskEvent.findMany({
      where: {
        eventType: {
          in: [ADMIN_EVENT_APPROVAL_SUBMITTED, ADMIN_EVENT_APPROVAL_DECIDED, ADMIN_EVENT_CONFIG_ROLLBACK],
        },
      },
      orderBy: { createdAt: "desc" },
      take: parsed.data.limit,
    });

    const items: AdminAuditRow[] = events
      .map((event) => {
        const details = asObject(event.detailsJson);
        return {
          eventId: event.id,
          eventType: event.eventType,
          reasonCode: event.reasonCode,
          severity: event.severity,
          actor: typeof details.actor === "string" ? details.actor : typeof details.requestedBy === "string" ? details.requestedBy : null,
          actionType: typeof details.actionType === "string" ? details.actionType : null,
          reason: typeof details.reason === "string" ? details.reason : null,
          createdAtUtc: event.createdAt.toISOString(),
          details,
        };
      })
      .filter((item) => {
        if (parsed.data.actor && item.actor !== parsed.data.actor) {
          return false;
        }

        if (parsed.data.actionType && item.actionType !== parsed.data.actionType) {
          return false;
        }

        return true;
      });

    return {
      count: items.length,
      items,
    };
  });

  app.get("/admin/config-snapshots", async (req, reply) => {
    const parsed = listSnapshotsSchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const snapshots = await prismaClient().strategyConfig.findMany({
      where: {
        strategyId: parsed.data.strategyId,
        strategyVersion: parsed.data.strategyVersion,
      },
      orderBy: { createdAt: "desc" },
      take: parsed.data.limit,
    });

    return {
      count: snapshots.length,
      items: snapshots.map((snapshot) => ({
        id: snapshot.id,
        strategyId: snapshot.strategyId,
        strategyVersion: snapshot.strategyVersion,
        riskProfile: snapshot.riskProfile,
        createdAtUtc: snapshot.createdAt.toISOString(),
        config: snapshot.configJson,
      })),
    };
  });

  app.post("/admin/config-snapshots/rollback", async (req, reply) => {
    const parsed = rollbackSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const source = await prismaClient().strategyConfig.findUnique({ where: { id: parsed.data.configId } });
    if (!source) {
      return reply.status(404).send({ error: { code: "NOT_FOUND", message: "Config snapshot not found" } });
    }

    const rollbackSnapshot = await prismaClient().strategyConfig.create({
      data: {
        strategyId: source.strategyId,
        strategyVersion: source.strategyVersion,
        riskProfile: source.riskProfile ?? "balanced",
        configJson: source.configJson as Prisma.InputJsonValue,
      },
    });

    await prismaClient().riskEvent.create({
      data: {
        strategyId: source.strategyId,
        eventType: ADMIN_EVENT_CONFIG_ROLLBACK,
        reasonCode: "CONFIG_ROLLBACK_APPLIED",
        severity: "warning",
        detailsJson: {
          sourceConfigId: source.id,
          rollbackConfigId: rollbackSnapshot.id,
          actor: parsed.data.actor,
          reason: parsed.data.reason,
          strategyId: source.strategyId,
          strategyVersion: source.strategyVersion,
        },
      },
    });

    recordFileLog({
      category: "security",
      level: "warn",
      event: "admin_config_rollback",
      message: "Configuration rollback recorded",
      context: {
        sourceConfigId: source.id,
        rollbackConfigId: rollbackSnapshot.id,
        actor: parsed.data.actor,
        reason: parsed.data.reason,
        strategyId: source.strategyId,
        strategyVersion: source.strategyVersion,
      },
    });

    return {
      ok: true,
      snapshot: {
        id: rollbackSnapshot.id,
        strategyId: rollbackSnapshot.strategyId,
        strategyVersion: rollbackSnapshot.strategyVersion,
        riskProfile: rollbackSnapshot.riskProfile,
        createdAtUtc: rollbackSnapshot.createdAt.toISOString(),
        config: rollbackSnapshot.configJson,
      },
    };
  });
}

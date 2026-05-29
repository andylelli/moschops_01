import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { recordFileLog } from "../services/file-log";

const INCIDENT_ACKNOWLEDGED_EVENT = "INCIDENT_ACKNOWLEDGED";

const listIncidentsQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

const acknowledgeIncidentParamsSchema = z.object({
  incidentId: z.string().min(1),
});

const acknowledgeIncidentBodySchema = z.object({
  actor: z.string().min(1),
  note: z.string().min(5),
});

type IncidentItem = {
  incidentId: string;
  severity: string;
  eventType: string;
  reasonCode: string;
  summary: string;
  createdAtUtc: string;
  runbookId: string;
  acknowledged: boolean;
  acknowledgedBy: string | null;
  acknowledgedAtUtc: string | null;
  latestNote: string | null;
};

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {};
}

function mapRunbookId(eventType: string, reasonCode: string): string {
  const normalized = `${eventType}:${reasonCode}`.toUpperCase();

  if (normalized.includes("NEWS")) {
    return "RB-NEWS-002";
  }

  if (normalized.includes("AI") || normalized.includes("MODEL")) {
    return "RB-ML-004";
  }

  if (normalized.includes("RISK") || normalized.includes("KILL_SWITCH")) {
    return "RB-RISK-001";
  }

  if (normalized.includes("APPROVAL") || normalized.includes("ROLLBACK") || normalized.includes("CONFIG")) {
    return "RB-ADMIN-003";
  }

  return "RB-GENERAL-001";
}

function mapSummary(eventType: string, reasonCode: string, details: Record<string, unknown>): string {
  if (typeof details.summary === "string" && details.summary.trim().length > 0) {
    return details.summary;
  }

  if (typeof details.reason === "string" && details.reason.trim().length > 0) {
    return details.reason;
  }

  if (typeof details.failureReason === "string" && details.failureReason.trim().length > 0) {
    return details.failureReason;
  }

  return `${eventType} (${reasonCode})`;
}

export async function incidentsRoutes(app: FastifyInstance): Promise<void> {
  app.get("/incidents", async (req, reply) => {
    const parsed = listIncidentsQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const events = await prismaClient().riskEvent.findMany({
      where: {
        eventType: {
          not: INCIDENT_ACKNOWLEDGED_EVENT,
        },
      },
      orderBy: { createdAt: "desc" },
      take: parsed.data.limit,
    });

    const incidentIds = events.map((event) => event.id);
    const acknowledgements = incidentIds.length
      ? await prismaClient().riskEvent.findMany({
          where: {
            eventType: INCIDENT_ACKNOWLEDGED_EVENT,
          },
          orderBy: { createdAt: "desc" },
          take: Math.max(parsed.data.limit * 5, 200),
        })
      : [];

    const acknowledgementByIncidentId = new Map<string, { actor: string | null; note: string | null; acknowledgedAtUtc: string }>();

    const incidentIdSet = new Set(incidentIds);

    for (const acknowledgement of acknowledgements) {
      const details = asRecord(acknowledgement.detailsJson);
      const incidentId = typeof details.incidentId === "string" ? details.incidentId : null;
      if (!incidentId || !incidentIdSet.has(incidentId) || acknowledgementByIncidentId.has(incidentId)) {
        continue;
      }

      acknowledgementByIncidentId.set(incidentId, {
        actor: typeof details.actor === "string" ? details.actor : null,
        note: typeof details.note === "string" ? details.note : null,
        acknowledgedAtUtc: acknowledgement.createdAt.toISOString(),
      });
    }

    const items: IncidentItem[] = events.map((event) => {
      const details = asRecord(event.detailsJson);
      const acknowledgement = acknowledgementByIncidentId.get(event.id);

      return {
        incidentId: event.id,
        severity: event.severity,
        eventType: event.eventType,
        reasonCode: event.reasonCode,
        summary: mapSummary(event.eventType, event.reasonCode, details),
        createdAtUtc: event.createdAt.toISOString(),
        runbookId: mapRunbookId(event.eventType, event.reasonCode),
        acknowledged: Boolean(acknowledgement),
        acknowledgedBy: acknowledgement?.actor ?? null,
        acknowledgedAtUtc: acknowledgement?.acknowledgedAtUtc ?? null,
        latestNote: acknowledgement?.note ?? null,
      };
    });

    return {
      count: items.length,
      items,
    };
  });

  app.post("/incidents/:incidentId/acknowledge", async (req, reply) => {
    const params = acknowledgeIncidentParamsSchema.safeParse(req.params);
    if (!params.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: params.error.message } });
    }

    const body = acknowledgeIncidentBodySchema.safeParse(req.body);
    if (!body.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: body.error.message } });
    }

    const sourceIncident = await prismaClient().riskEvent.findUnique({
      where: { id: params.data.incidentId },
    });

    if (!sourceIncident) {
      return reply.status(404).send({ error: { code: "NOT_FOUND", message: "Incident not found" } });
    }

    await prismaClient().riskEvent.create({
      data: {
        decisionId: sourceIncident.decisionId,
        strategyId: sourceIncident.strategyId,
        eventType: INCIDENT_ACKNOWLEDGED_EVENT,
        reasonCode: "INCIDENT_ACKNOWLEDGED",
        severity: "info",
        detailsJson: {
          incidentId: sourceIncident.id,
          actor: body.data.actor,
          note: body.data.note,
          sourceEventType: sourceIncident.eventType,
          sourceReasonCode: sourceIncident.reasonCode,
        },
      },
    });

    recordFileLog({
      category: "audit",
      level: "info",
      event: "incident_acknowledged",
      message: "Incident acknowledged",
      context: {
        incidentId: sourceIncident.id,
        acknowledgedBy: body.data.actor,
        note: body.data.note,
        sourceEventType: sourceIncident.eventType,
        sourceReasonCode: sourceIncident.reasonCode,
      },
    });

    return {
      ok: true,
      incidentId: sourceIncident.id,
      acknowledgedBy: body.data.actor,
      note: body.data.note,
      acknowledgedAtUtc: new Date().toISOString(),
    };
  });
}
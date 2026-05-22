import type { FastifyInstance } from "fastify";
import { getNewsProviderSnapshot, listActiveGuardWindows, listUpcomingNews } from "../services/news-state";

export async function newsRoutes(app: FastifyInstance): Promise<void> {
  app.get("/news/providers", async () => {
    const provider = await getNewsProviderSnapshot();

    return {
      count: 1,
      items: [provider],
      fetchedAtUtc: new Date().toISOString(),
    };
  });

  app.get("/news/upcoming", async () => {
    const items = await listUpcomingNews();

    return {
      count: items.length,
      items,
      fetchedAtUtc: new Date().toISOString(),
    };
  });

  app.get("/news/active", async () => {
    const items = await listActiveGuardWindows();

    return {
      count: items.length,
      items,
      fetchedAtUtc: new Date().toISOString(),
    };
  });
}